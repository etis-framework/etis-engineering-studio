from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..services.auth import (
    require_staff, require_course_owner_ctx, require_section_role,
    accessible_section_ids,
)
from ..config import get_settings
from ..models import (
    User, Team, TeamMembership, TeamSection, CourseTerm, CourseSection,
    SectionEnrollment, SectionStaff, PhaseSchedule, InstitutionalIdentity,
)
from ..services.course_admin import (
    ensure_term, ensure_section, generate_schedule, import_roster,
    roster_rows, assign_team, phase_access, display_name,
)
from ..services.seed import ensure_demo

router=APIRouter(prefix="/api/v1/admin",tags=["course administration"])

MANAGE_SECTION_ROLES={"course_owner","instructor"}
READ_SECTION_ROLES={"course_owner","instructor","ta","reviewer"}

class TermCreate(BaseModel):
    namespace:str=Field(min_length=3,max_length=60)
    term_label:str=Field(min_length=3,max_length=100)
    starts_on:str
    ends_on:str=""
    course_code:str="COMP 330"

class SectionCreate(BaseModel):
    section_key:str=Field(min_length=1,max_length=40)
    display_name:str|None=None
    meeting_pattern:str=""

class TeamCreate(BaseModel):
    team_key:str=Field(min_length=1,max_length=40)
    name:str|None=None

class TeamAssignment(BaseModel):
    team_id:int|None=None

class PhaseUpdate(BaseModel):
    available_at:datetime|None=None
    due_at:datetime|None=None
    accept_until:datetime|None=None
    release_override:str=Field(default="auto",pattern=r"^(auto|released|locked)$")
    instructor_note:str=""

class StudentAdd(BaseModel):
    student_id:str=Field(min_length=2,max_length=120)
    name:str=Field(min_length=2,max_length=200)
    team_id:int|None=None

class StaffAdd(BaseModel):
    email:str
    display_name:str=""
    role:str=Field(pattern=r"^(course_owner|instructor|ta|reviewer)$")


def _section(db:Session,section_id:int)->CourseSection:
    section=db.get(CourseSection,section_id)
    if not section: raise HTTPException(404,"Section not found")
    return section


def _term(db:Session,term_id:int)->CourseTerm:
    term=db.get(CourseTerm,term_id)
    if not term: raise HTTPException(404,"Term not found")
    return term


def _can_view_section(db:Session,ctx:dict,section_id:int):
    return require_section_role(db,ctx,section_id,READ_SECTION_ROLES)


def _can_manage_section(db:Session,ctx:dict,section_id:int):
    return require_section_role(db,ctx,section_id,MANAGE_SECTION_ROLES)


@router.get("/setup")
def setup(db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    # Keep the development demo convenient; production authorization is still explicit.
    if ctx.get("role")=="developer": ensure_demo(db)
    s=get_settings(); allowed=accessible_section_ids(db,ctx)
    terms=db.query(CourseTerm).order_by(CourseTerm.id.desc()).all()
    result=[]
    for t in terms:
        sections=db.query(CourseSection).filter_by(term_id=t.id).all()
        if allowed is not None: sections=[x for x in sections if x.id in allowed]
        if allowed is not None and not sections: continue
        result.append({
            "id":t.id,"namespace":t.namespace,"course_code":t.course_code,"term_label":t.term_label,
            "starts_on":t.starts_on,"ends_on":t.ends_on,"status":t.status,
            "sections":[{"id":x.id,"section_key":x.section_key,"display_name":x.display_name,"meeting_pattern":x.meeting_pattern,"active":x.is_active,"phase_access":phase_access(db,x.id)} for x in sections],
        })
    return {"terms":result,"default_namespace":s.etis_course_namespace,"can_create_term":ctx.get("role")=="developer" or allowed is None}


@router.post("/terms")
def create_term(req:TermCreate,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    require_course_owner_ctx(db,ctx)
    if db.query(CourseTerm).filter_by(namespace=req.namespace).first(): raise HTTPException(409,"A term with that namespace already exists")
    term=CourseTerm(course_code=req.course_code,namespace=req.namespace,term_label=req.term_label,starts_on=req.starts_on,ends_on=req.ends_on,status="setup")
    db.add(term); db.commit(); return {"id":term.id,"namespace":term.namespace,"term_label":term.term_label}


@router.post("/terms/default")
def default_term(db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    require_course_owner_ctx(db,ctx)
    s=get_settings(); term=ensure_term(db,s.etis_course_namespace); section=ensure_section(db,term); generate_schedule(db,section,term.starts_on or "2026-08-25")
    if ctx.get("uid") and not db.query(SectionStaff).filter_by(section_id=section.id,user_id=ctx["uid"],staff_role="course_owner").first():
        db.add(SectionStaff(section_id=section.id,user_id=ctx["uid"],staff_role="course_owner",is_active=True))
    db.commit(); return {"term_id":term.id,"section_id":section.id}


@router.post("/terms/{term_id}/sections")
def create_section(term_id:int,req:SectionCreate,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    require_course_owner_ctx(db,ctx); term=_term(db,term_id)
    if db.query(CourseSection).filter_by(term_id=term_id,section_key=req.section_key).first(): raise HTTPException(409,"Section already exists")
    section=CourseSection(term_id=term_id,section_key=req.section_key,display_name=req.display_name or f"{term.course_code} · {term.term_label} · Section {req.section_key}",meeting_pattern=req.meeting_pattern)
    db.add(section); db.flush(); generate_schedule(db,section,term.starts_on or "2026-08-25")
    if ctx.get("uid"): db.add(SectionStaff(section_id=section.id,user_id=ctx["uid"],staff_role="course_owner",is_active=True))
    db.commit(); return {"id":section.id,"section_key":section.section_key}


@router.post("/sections/{section_id}/roster")
def upload_roster(section_id:int,file:UploadFile=File(...),deactivate_missing:bool=False,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    section=_section(db,section_id); _can_manage_section(db,ctx,section_id)
    try: result=import_roster(db,section,file.file.read(),deactivate_missing=deactivate_missing)
    except ValueError as e: raise HTTPException(400,str(e)) from e
    db.commit(); return result


@router.get("/sections/{section_id}/students")
def students(section_id:int,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _section(db,section_id); _can_view_section(db,ctx,section_id)
    return {"students":roster_rows(db,section_id)}


@router.post("/sections/{section_id}/teams")
def create_team(section_id:int,req:TeamCreate,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    section=_section(db,section_id); _can_manage_section(db,ctx,section_id); term=_term(db,section.term_id)
    team=Team(course_namespace=term.namespace,team_key=req.team_key,name=req.name or req.team_key.replace('-',' ').title(),project_name="Project not confirmed",current_phase="A1")
    db.add(team); db.flush(); db.add(TeamSection(team_id=team.id,section_id=section_id)); db.commit(); return {"id":team.id,"team_key":team.team_key,"name":team.name}


@router.get("/sections/{section_id}/teams")
def teams(section_id:int,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _section(db,section_id); _can_view_section(db,ctx,section_id)
    pairs=db.query(Team).join(TeamSection,TeamSection.team_id==Team.id).filter(TeamSection.section_id==section_id,Team.is_active==True).all()
    return {"teams":[{"id":t.id,"team_key":t.team_key,"name":t.name,"project_name":t.project_name,"repo_full_name":t.repo_full_name,"members":db.query(TeamMembership).filter_by(team_id=t.id).count()} for t in pairs]}


@router.post("/sections/{section_id}/students")
def add_student(section_id:int,req:StudentAdd,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _section(db,section_id); _can_manage_section(db,ctx,section_id)
    sid=req.student_id.strip().lower(); ident=db.query(InstitutionalIdentity).filter_by(student_id=sid).first()
    if ident: user=db.get(User,ident.user_id); user.display_name=display_name(req.name)
    else:
        user=User(github_login=f"luc:{sid}",display_name=display_name(req.name),role="student"); db.add(user); db.flush(); db.add(InstitutionalIdentity(user_id=user.id,student_id=sid,institutional_email=f"{sid}@luc.edu"))
    enr=db.query(SectionEnrollment).filter_by(section_id=section_id,user_id=user.id).first()
    if not enr: db.add(SectionEnrollment(section_id=section_id,user_id=user.id,status="active"))
    else: enr.status="active"; enr.left_at=None
    db.flush()
    if req.team_id:
        if not db.query(TeamSection).filter_by(team_id=req.team_id,section_id=section_id).first(): raise HTTPException(400,"Target team does not belong to this section")
        assign_team(db,section_id,user.id,req.team_id,ctx.get("uid"))
    db.commit(); return {"user_id":user.id,"student_id":sid,"name":user.display_name,"team_id":req.team_id}


@router.put("/sections/{section_id}/students/{user_id}/team")
def move_student(section_id:int,user_id:int,req:TeamAssignment,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _can_manage_section(db,ctx,section_id)
    enr=db.query(SectionEnrollment).filter_by(section_id=section_id,user_id=user_id).first()
    if not enr: raise HTTPException(404,"Student is not enrolled in this section")
    if req.team_id and not db.query(TeamSection).filter_by(team_id=req.team_id,section_id=section_id).first(): raise HTTPException(400,"Target team does not belong to this section")
    result=assign_team(db,section_id,user_id,req.team_id,ctx.get("uid")); db.commit(); return result


@router.put("/sections/{section_id}/students/{user_id}/status")
def student_status(section_id:int,user_id:int,status:str,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _can_manage_section(db,ctx,section_id)
    if status not in {"active","dropped"}: raise HTTPException(400,"Status must be active or dropped")
    enr=db.query(SectionEnrollment).filter_by(section_id=section_id,user_id=user_id).first()
    if not enr: raise HTTPException(404,"Enrollment not found")
    enr.status=status; enr.left_at=datetime.now(timezone.utc) if status=="dropped" else None; db.commit(); return {"status":status}


@router.get("/sections/{section_id}/schedule")
def schedule(section_id:int,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _can_view_section(db,ctx,section_id); return phase_access(db,section_id)


@router.put("/sections/{section_id}/schedule/{phase_id}")
def update_phase(section_id:int,phase_id:str,req:PhaseUpdate,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _can_manage_section(db,ctx,section_id)
    row=db.query(PhaseSchedule).filter_by(section_id=section_id,phase_id=phase_id.upper()).first()
    if not row: raise HTTPException(404,"Phase schedule not found")
    row.available_at=req.available_at; row.due_at=req.due_at; row.accept_until=req.accept_until; row.release_override=req.release_override; row.instructor_note=req.instructor_note; db.commit(); return {"phase_id":row.phase_id,"release_override":row.release_override}


@router.get("/sections/{section_id}/staff")
def staff(section_id:int,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _can_view_section(db,ctx,section_id)
    rows=db.query(SectionStaff).filter_by(section_id=section_id,is_active=True).all()
    out=[]
    for r in rows:
        user=db.get(User,r.user_id); ident=db.query(InstitutionalIdentity).filter_by(user_id=r.user_id).first()
        out.append({"user_id":r.user_id,"name":user.display_name if user else "","email":ident.institutional_email if ident else None,"role":r.staff_role})
    return {"staff":out}


@router.post("/sections/{section_id}/staff")
def add_staff(section_id:int,req:StaffAdd,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    _section(db,section_id)
    # Course Owner controls elevated roles. Instructors may add bounded TA/reviewer access to their own section.
    if req.role in {"course_owner","instructor"}: require_course_owner_ctx(db,ctx)
    else: require_section_role(db,ctx,section_id,{"course_owner","instructor"})
    email=req.email.strip().lower(); ident=db.query(InstitutionalIdentity).filter_by(institutional_email=email).first()
    if ident: user=db.get(User,ident.user_id)
    else:
        login=f"staff:{email}"; user=db.query(User).filter_by(github_login=login).first()
        if not user:
            user=User(github_login=login,display_name=req.display_name or email.split('@')[0],role="instructor" if req.role in {"course_owner","instructor"} else req.role); db.add(user); db.flush()
        sid=email.split('@')[0]; db.add(InstitutionalIdentity(user_id=user.id,student_id=f"staff:{sid}",institutional_email=email))
    row=db.query(SectionStaff).filter_by(section_id=section_id,user_id=user.id,staff_role=req.role).first()
    if not row: db.add(SectionStaff(section_id=section_id,user_id=user.id,staff_role=req.role,is_active=True))
    else: row.is_active=True
    db.commit(); return {"user_id":user.id,"name":user.display_name,"email":email,"role":req.role}


@router.put("/terms/{term_id}/status")
def term_status(term_id:int,status:str,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    require_course_owner_ctx(db,ctx)
    if status not in {"setup","active","archived"}: raise HTTPException(400,"Invalid term status")
    term=_term(db,term_id); term.status=status; db.commit(); return {"id":term.id,"status":term.status}
