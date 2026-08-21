from __future__ import annotations
import csv, io, re
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from ..models import (
    User, Team, TeamMembership, CourseTerm, CourseSection, InstitutionalIdentity,
    SectionEnrollment, SectionStaff, TeamSection, MembershipEvent, PhaseSchedule,
    GitHubIdentity, RepositoryConnection,
)

PHASE_OFFSETS = {
    "A1": (16, 26, 33), "A2": (28, 35, 44), "A3": (37, 51, 58),
    "A4": (58, 65, 72), "A5": (70, 77, 77), "A6": (72, 91, 98),
}


def display_name(raw: str) -> str:
    raw=(raw or "").strip()
    if "," in raw:
        last, first = [x.strip() for x in raw.split(",",1)]
        return f"{first} {last}".strip()
    return raw


def ensure_term(db: Session, namespace: str, term_label: str = "Fall 2026", starts_on: str = "2026-08-25") -> CourseTerm:
    term=db.query(CourseTerm).filter_by(namespace=namespace).first()
    if not term:
        term=CourseTerm(namespace=namespace,term_label=term_label,starts_on=starts_on,status="active")
        db.add(term); db.flush()
    return term


def ensure_section(db: Session, term: CourseTerm, section_key: str="001", display: str|None=None) -> CourseSection:
    section=db.query(CourseSection).filter_by(term_id=term.id,section_key=section_key).first()
    if not section:
        section=CourseSection(term_id=term.id,section_key=section_key,display_name=display or f"COMP 330 · {term.term_label} · Section {section_key}")
        db.add(section); db.flush()
    return section


def generate_schedule(db: Session, section: CourseSection, starts_on: str, overwrite: bool=False):
    """Propose section dates from the COMP 330 cadence in the term's local timezone.

    Availability opens at 12:05 AM local time and deadline-style fields default to
    11:55 PM local time.  Instructors can override every phase independently.
    """
    term=db.get(CourseTerm,section.term_id)
    tz=ZoneInfo((term.timezone if term else None) or "America/Chicago")
    start_date=datetime.fromisoformat(starts_on).date()
    rows=[]
    for phase,(a,d,u) in PHASE_OFFSETS.items():
        row=db.query(PhaseSchedule).filter_by(section_id=section.id,phase_id=phase).first()
        if row and not overwrite:
            rows.append(row); continue
        if not row:
            row=PhaseSchedule(section_id=section.id,phase_id=phase); db.add(row)
        row.available_at=datetime.combine(start_date+timedelta(days=a),time(0,5),tzinfo=tz)
        row.due_at=datetime.combine(start_date+timedelta(days=d),time(23,55),tzinfo=tz)
        row.accept_until=datetime.combine(start_date+timedelta(days=u),time(23,55),tzinfo=tz)
        row.release_override="auto"
        rows.append(row)
    db.flush(); return rows


def phase_access(db: Session, section_id: int, now: datetime|None=None):
    now=now or datetime.now(timezone.utc)
    section=db.get(CourseSection,section_id); term=db.get(CourseTerm,section.term_id) if section else None
    local_tz=ZoneInfo((term.timezone if term else None) or "America/Chicago")
    rows=db.query(PhaseSchedule).filter_by(section_id=section_id).order_by(PhaseSchedule.phase_id).all()
    result=[]
    for row in rows:
        if row.release_override=="released": status="released"
        elif row.release_override=="locked": status="locked"
        else:
            available=row.available_at
            # SQLite does not preserve timezone offsets.  Schedule timestamps are authored
            # in the section/term timezone, so restore that semantic timezone here.
            if available and available.tzinfo is None:
                available=available.replace(tzinfo=local_tz)
            status="released" if available and available <= now else "locked"
        result.append({"phase_id":row.phase_id,"status":status,"available_at":row.available_at.isoformat() if row.available_at else None,"due_at":row.due_at.isoformat() if row.due_at else None,"accept_until":row.accept_until.isoformat() if row.accept_until else None,"override":row.release_override})
    released=[x["phase_id"] for x in result if x["status"]=="released"]
    return {"phases":result,"current_phase":released[-1] if released else "A1","released":released}


def import_roster(db: Session, section: CourseSection, raw: bytes, deactivate_missing: bool=False):
    text=raw.decode("utf-8-sig")
    reader=csv.DictReader(io.StringIO(text))
    headers={h.strip().lower():h for h in (reader.fieldnames or [])}
    sid_col=headers.get("student id")
    name_col=headers.get("name")
    if not sid_col or not name_col:
        raise ValueError("Roster CSV must contain Student ID and Name columns")
    seen=set(); added=reactivated=unchanged=0
    for row in reader:
        sid=(row.get(sid_col) or "").strip().lower()
        if not sid: continue
        seen.add(sid)
        ident=db.query(InstitutionalIdentity).filter_by(student_id=sid).first()
        if ident:
            user=db.get(User,ident.user_id)
            user.display_name=display_name(row.get(name_col) or sid)
        else:
            placeholder=f"luc:{sid}"
            user=db.query(User).filter_by(github_login=placeholder).first()
            if not user:
                user=User(github_login=placeholder,display_name=display_name(row.get(name_col) or sid),role="student")
                db.add(user); db.flush()
            ident=InstitutionalIdentity(user_id=user.id,student_id=sid,institutional_email=f"{sid}@luc.edu")
            db.add(ident); db.flush()
        enr=db.query(SectionEnrollment).filter_by(section_id=section.id,user_id=user.id).first()
        if not enr:
            db.add(SectionEnrollment(section_id=section.id,user_id=user.id,status="active")); added+=1
        elif enr.status!="active":
            enr.status="active"; enr.left_at=None; reactivated+=1
        else: unchanged+=1
    dropped=0
    if deactivate_missing:
        enrollments=db.query(SectionEnrollment).filter_by(section_id=section.id,status="active").all()
        for enr in enrollments:
            ident=db.query(InstitutionalIdentity).filter_by(user_id=enr.user_id).first()
            if ident and ident.student_id not in seen:
                enr.status="dropped"; enr.left_at=datetime.now(timezone.utc); dropped+=1
    db.flush()
    return {"rows":len(seen),"added":added,"reactivated":reactivated,"unchanged":unchanged,"deactivated":dropped}


def assign_team(db: Session, section_id: int, user_id: int, team_id: int|None, performed_by: int|None=None):
    current=(db.query(TeamMembership).join(Team,TeamMembership.team_id==Team.id).join(TeamSection,TeamSection.team_id==Team.id).filter(TeamSection.section_id==section_id,TeamMembership.user_id==user_id).first())
    from_team=current.team_id if current else None
    if current and (team_id is None or current.team_id!=team_id): db.delete(current)
    if team_id and from_team!=team_id:
        db.add(TeamMembership(team_id=team_id,user_id=user_id,responsibility_role="Engineering Contributor",is_primary=True))
    action="removed" if team_id is None else ("moved" if from_team and from_team!=team_id else "assigned")
    db.add(MembershipEvent(section_id=section_id,user_id=user_id,from_team_id=from_team,to_team_id=team_id,action=action,performed_by_user_id=performed_by))
    db.flush(); return {"from_team_id":from_team,"to_team_id":team_id,"action":action}


def roster_rows(db: Session, section_id: int):
    enrs=db.query(SectionEnrollment).filter_by(section_id=section_id).all()
    rows=[]
    for enr in enrs:
        u=db.get(User,enr.user_id); ident=db.query(InstitutionalIdentity).filter_by(user_id=u.id).first(); gh=db.query(GitHubIdentity).filter_by(user_id=u.id).first()
        tm=(db.query(TeamMembership,Team).join(Team,TeamMembership.team_id==Team.id).join(TeamSection,TeamSection.team_id==Team.id).filter(TeamSection.section_id==section_id,TeamMembership.user_id==u.id).first())
        rows.append({"user_id":u.id,"student_id":ident.student_id if ident else "","email":ident.institutional_email if ident else "","name":u.display_name,"status":enr.status,"github_login":gh.github_login if gh else None,"team_id":tm.Team.id if tm else None,"team_key":tm.Team.team_key if tm else None,"team_name":tm.Team.name if tm else None})
    return sorted(rows,key=lambda x:x["name"])


def repo_name_from_clone(value: str) -> tuple[str, str]:
    """Return a canonical GitHub owner/repository name and HTTPS clone URL.

    Repository nomination is a security boundary. Accept only an unambiguous
    HTTPS github.com URL containing exactly one owner and one repository path.
    Credentials, ports, query strings, fragments, extra path segments, and
    malformed GitHub account/repository names are rejected server-side.
    """
    value = (value or "").strip()

    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValueError(
            "Use the HTTPS Git clone URL, for example "
            "https://github.com/owner/repository.git"
        ) from exc

    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ValueError(
            "Use an HTTPS GitHub repository URL with no credentials, port, "
            "query string, or fragment"
        ) from exc

    if (
        parsed.scheme.casefold() != "https"
        or parsed.hostname is None
        or parsed.hostname.casefold() != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed_port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Use an HTTPS GitHub repository URL with no credentials, port, "
            "query string, or fragment"
        )

    normalized_path = parsed.path[:-1] if parsed.path.endswith("/") else parsed.path
    parts = normalized_path.split("/")
    if (
        len(parts) != 3
        or parts[0] != ""
        or not parts[1]
        or not parts[2]
    ):
        raise ValueError(
            "Use the HTTPS Git clone URL, for example "
            "https://github.com/owner/repository.git"
        )

    owner, repo = parts[1], parts[2]
    if repo.casefold().endswith(".git"):
        repo = repo[:-4]

    owner_pattern = re.compile(
        r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$"
    )
    repo_pattern = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

    if not owner_pattern.fullmatch(owner) or "--" in owner:
        raise ValueError("GitHub repository owner name is invalid")
    if repo in {".", ".."} or not repo_pattern.fullmatch(repo):
        raise ValueError("GitHub repository name is invalid")

    return f"{owner}/{repo}", f"https://github.com/{owner}/{repo}.git"


def suggest_project_name(repo_full_name: str) -> str:
    """Best-effort project-name proposal from README H1; falls back to repository name.

    This is deterministic onboarding assistance, not authoritative engineering evidence.
    """
    import base64
    import httpx
    from ..config import get_settings
    settings=get_settings(); headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    if settings.github_app_id and settings.github_app_private_key:
        try:
            from .github_app import manager as github_app_manager
            headers["Authorization"]=f"Bearer {github_app_manager.token_for_repo(repo_full_name).token}"
        except Exception:
            pass
    try:
        with httpx.Client(base_url="https://api.github.com",headers=headers,timeout=12.0,follow_redirects=True) as c:
            r=c.get(f"/repos/{repo_full_name}/readme")
            if r.is_success:
                data=r.json(); raw=base64.b64decode(data.get("content","")).decode("utf-8",errors="replace")
                for line in raw.splitlines():
                    t=line.strip()
                    if t.startswith("# "):
                        title=t[2:].strip()
                        if title and len(title)<=160 and "comp 330" not in title.lower(): return title
    except Exception:
        pass
    repo=repo_full_name.split("/",1)[-1]
    return repo.replace("-"," ").replace("_"," ").title()
