import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..services.auth import require_staff, accessible_section_ids, require_section_role
from ..models import Team, User, TeamMembership, ReviewSession, ReviewTurn, EvidenceSnapshot, TeamSection, CourseSection, SectionEnrollment
from ..services.usage_store import usage_summary
from ..config import get_settings
from ..services.seed import ensure_demo

router=APIRouter(prefix="/api/v1/instructor",tags=["instructor"])
READ_ROLES={"course_owner","instructor","ta","reviewer"}


def _safe_json(value, default):
    try: return json.loads(value or "")
    except Exception: return default


def _team_summary(db: Session, team: Team):
    sessions=db.query(ReviewSession).filter_by(team_id=team.id).order_by(ReviewSession.started_at.desc()).all()
    members=db.query(TeamMembership).filter_by(team_id=team.id).all()
    latest_snapshot=db.query(EvidenceSnapshot).filter_by(team_id=team.id).order_by(EvidenceSnapshot.created_at.desc()).first()
    evidence=_safe_json(latest_snapshot.summary_json,{}) if latest_snapshot else {}
    latest_session=sessions[0] if sessions else None; state=_safe_json(latest_session.challenge_state_json,{}) if latest_session else {}; evaluation=state.get("evaluation") or {}
    gaps=[x for x in evidence.get("items",[]) if x.get("status") not in {"present","verified"}]
    coverage=evidence.get("coverage"); disposition=evaluation.get("disposition"); attention="healthy"; reasons=[]
    if coverage is not None and coverage < 60: attention="attention"; reasons.append("material evidence gaps")
    if disposition in {"insufficient_defense","needs_challenge"}: attention="attention"; reasons.append("decision defense needs follow-up")
    if latest_session and latest_session.status=="active": reasons.append("review in progress")
    usage=usage_summary(db,team_id=team.id)
    return {"id":team.id,"team_key":team.team_key,"name":team.name,"project":team.project_name,"phase":team.current_phase,"repo":team.repo_full_name,"members":len(members),"review_sessions":len(sessions),"active_sessions":sum(s.status=="active" for s in sessions),"last_activity":latest_session.started_at.isoformat() if latest_session else None,"evidence_coverage":coverage,"evidence_gaps":len(gaps),"last_disposition":disposition,"attention":attention,"attention_reasons":reasons,"ai_usage":usage}


def _visible_sections(db:Session,ctx:dict):
    allowed=accessible_section_ids(db,ctx)
    q=db.query(CourseSection).filter_by(is_active=True)
    if allowed is not None: q=q.filter(CourseSection.id.in_(list(allowed))) if allowed else q.filter(CourseSection.id==-1)
    return q.all(),allowed


@router.get("/overview")
def overview(section_id:int|None=None,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    if ctx.get("role")=="developer": ensure_demo(db)
    sections,allowed=_visible_sections(db,ctx)
    if section_id is not None:
        if allowed is not None and section_id not in allowed: raise HTTPException(403,"You are not assigned to this section")
        if not any(s.id==section_id for s in sections): raise HTTPException(404,"Section not found")
        team_ids=[x.team_id for x in db.query(TeamSection).filter_by(section_id=section_id).all()]
    else:
        section_ids=[s.id for s in sections]
        team_ids=[x.team_id for x in db.query(TeamSection).filter(TeamSection.section_id.in_(section_ids)).all()] if section_ids else []
    teams=db.query(Team).filter(Team.id.in_(team_ids),Team.is_active==True).all() if team_ids else []
    out=[_team_summary(db,t) for t in teams]
    course_usage=usage_summary(db,team_ids=team_ids); settings=get_settings()
    return {"course_namespace":settings.etis_course_namespace,"teams":out,"sections":[{"id":sec.id,"section_key":sec.section_key,"display_name":sec.display_name,"students":db.query(SectionEnrollment).filter_by(section_id=sec.id,status="active").count()} for sec in sections],"selected_section_id":section_id,"class_signals":{"teams":len(out),"students":sum(db.query(TeamMembership).filter_by(team_id=t["id"]).count() for t in out),"teams_needing_attention":sum(t["attention"]=="attention" for t in out),"active_reviews":sum(t["active_sessions"] for t in out),"review_sessions":sum(t["review_sessions"] for t in out),"repositories_connected":sum(bool(t["repo"]) for t in out)},"ai_usage":course_usage,"cost_guardrails":{"team_warning_usd":settings.etis_ai_warning_team_usd,"course_warning_usd":settings.etis_ai_warning_course_usd,"course_warning":course_usage["estimated_cost_usd"]>=settings.etis_ai_warning_course_usd},"principle":"Instructor analytics support judgment; they do not reduce contribution to commit counts or lines of code."}


@router.get("/teams/{team_id}")
def team_detail(team_id:int,db:Session=Depends(get_db),ctx:dict=Depends(require_staff)):
    if ctx.get("role")=="developer": ensure_demo(db)
    team=db.get(Team,team_id)
    if not team: raise HTTPException(404,"Team not found")
    link=db.query(TeamSection).filter_by(team_id=team_id).first()
    if not link: raise HTTPException(404,"Team is not attached to an active course section")
    require_section_role(db,ctx,link.section_id,READ_ROLES)
    memberships=db.query(TeamMembership).filter_by(team_id=team.id).all(); members=[]
    for m in memberships:
        u=db.get(User,m.user_id); members.append({"id":u.id,"name":u.display_name,"github_login":u.github_login,"role":m.responsibility_role,"primary":m.is_primary})
    sessions=db.query(ReviewSession).filter_by(team_id=team.id).order_by(ReviewSession.started_at.desc()).limit(10).all(); session_rows=[]
    for s in sessions:
        state=_safe_json(s.challenge_state_json,{}); ev=state.get("evaluation") or {}; turn_count=db.query(ReviewTurn).filter_by(session_id=s.id).count()
        session_rows.append({"id":s.id,"phase":s.phase_id,"status":s.status,"mode":s.mode,"started_at":s.started_at.isoformat(),"turns":turn_count,"disposition":ev.get("disposition"),"learning_score":ev.get("learning_score"),"learning_score_max":ev.get("learning_score_max"),"missing_moves":ev.get("missing_moves",[])})
    snap=db.query(EvidenceSnapshot).filter_by(team_id=team.id).order_by(EvidenceSnapshot.created_at.desc()).first(); evidence=_safe_json(snap.summary_json,{}) if snap else None
    return {"team":_team_summary(db,team),"members":members,"sessions":session_rows,"evidence":evidence}
