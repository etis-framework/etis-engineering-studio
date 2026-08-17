from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..config import get_settings
from ..models import User, Team, TeamMembership, TeamSection, CourseSection, SectionEnrollment, InstitutionalIdentity, GitHubIdentity, RepositoryConnection
from ..services.course_admin import phase_access, repo_name_from_clone, suggest_project_name
from ..services.auth import require_authenticated, STAFF_ROLES
from ..services.evidence import GitHubEvidenceProvider

router=APIRouter(prefix="/api/v1/onboarding",tags=["onboarding"])

class ConnectRepository(BaseModel):
    clone_url:str=Field(min_length=10,max_length=500)
    user_id:int|None=None

class ConfirmProject(BaseModel):
    project_name:str=Field(min_length=2,max_length=200)
    team_name:str|None=Field(default=None,max_length=200)

@router.get("/users/{user_id}")
def user_context(user_id:int,request:Request,db:Session=Depends(get_db)):
    ctx=require_authenticated(request)
    if ctx.get("role") not in STAFF_ROLES|{"developer"} and ctx.get("uid")!=user_id: raise HTTPException(403,"Students may only view their own onboarding context")
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,"User not found")
    ident=db.query(InstitutionalIdentity).filter_by(user_id=user_id).first(); gh=db.query(GitHubIdentity).filter_by(user_id=user_id).first()
    enrollments=db.query(SectionEnrollment).filter_by(user_id=user_id,status="active").all()
    sections=[]
    for enr in enrollments:
        sec=db.get(CourseSection,enr.section_id)
        tm=(db.query(TeamMembership,Team).join(Team,TeamMembership.team_id==Team.id).join(TeamSection,TeamSection.team_id==Team.id).filter(TeamSection.section_id==sec.id,TeamMembership.user_id==user_id).first())
        team=tm.Team if tm else None
        conn=db.query(RepositoryConnection).filter_by(team_id=team.id).first() if team else None
        settings=get_settings(); install_url=f"https://github.com/apps/{settings.github_app_slug}/installations/new" if settings.github_app_slug else None
        members=[]
        if team:
            for membership in db.query(TeamMembership).filter_by(team_id=team.id).all():
                member=db.get(User,membership.user_id); member_gh=db.query(GitHubIdentity).filter_by(user_id=membership.user_id).first()
                if member:
                    members.append({"user_id":member.id,"name":member.display_name,"responsibility_role":membership.responsibility_role,"github_login":member_gh.github_login if member_gh else None})
        sections.append({"section":{"id":sec.id,"section_key":sec.section_key,"display_name":sec.display_name},"phase_access":phase_access(db,sec.id),"team":{"id":team.id,"team_key":team.team_key,"name":team.name,"project_name":team.project_name,"repo_full_name":team.repo_full_name,"members":members} if team else None,"repository":{"status":conn.status,"clone_url":conn.clone_url,"app_installed":conn.github_app_installed,"install_url":install_url} if conn else None})
    return {"user":{"id":user.id,"name":user.display_name,"role":user.role,"student_id":ident.student_id if ident else None,"email":ident.institutional_email if ident else None,"github_login":gh.github_login if gh else None},"sections":sections,"onboarding":{"institutional_identity":bool(ident),"github_identity":bool(gh),"team_assigned":any(x["team"] for x in sections),"repository_connected":any(x["repository"] and x["repository"]["status"] in {"verified","connected"} for x in sections)}}

@router.post("/teams/{team_id}/repository")
def connect_repository(team_id:int,req:ConnectRepository,request:Request,db:Session=Depends(get_db)):
    ctx=require_authenticated(request)
    if ctx.get("role") not in STAFF_ROLES|{"developer"}:
        if not db.query(TeamMembership).filter_by(team_id=team_id,user_id=ctx.get("uid")).first(): raise HTTPException(403,"Only a member of this team may connect its repository")
        if not db.query(GitHubIdentity).filter_by(user_id=ctx.get("uid")).first(): raise HTTPException(409,"Connect your GitHub identity before connecting the team repository")
        req.user_id=ctx.get("uid")
    # Lock the team row while binding the one authoritative repository so two
    # teammates onboarding at the same moment cannot create competing bindings.
    team=db.query(Team).filter_by(id=team_id).with_for_update().first()
    if not team: raise HTTPException(404,"Team not found")
    try: full_name,clone=repo_name_from_clone(req.clone_url)
    except ValueError as e: raise HTTPException(400,str(e)) from e
    existing=db.query(RepositoryConnection).filter_by(team_id=team_id).first()
    if existing and existing.repo_full_name!=full_name and existing.status in {"verified","connected"}: raise HTTPException(409,"This team already has an authoritative repository. An instructor must replace it.")
    status="identified"; verified=False
    try:
        GitHubEvidenceProvider().head_sha(full_name); status="verified"; verified=True
    except Exception:
        status="awaiting_access"
    if not existing:
        existing=RepositoryConnection(team_id=team_id,repo_full_name=full_name,clone_url=clone,status=status,connected_by_user_id=req.user_id,github_app_installed=False)
        db.add(existing)
    else:
        existing.repo_full_name=full_name; existing.clone_url=clone; existing.status=status; existing.connected_by_user_id=req.user_id
    if verified: existing.verified_at=datetime.now(timezone.utc)
    team.repo_full_name=full_name
    suggested_project=suggest_project_name(full_name) if verified else full_name.split("/",1)[-1].replace("-"," ").title()
    if not team.project_name or team.project_name in {"Project not confirmed","CampusConnect"}: team.project_name=suggested_project
    db.commit()
    settings=get_settings(); install_url=f"https://github.com/apps/{settings.github_app_slug}/installations/new" if settings.github_app_slug else None
    return {"repo_full_name":full_name,"clone_url":clone,"status":status,"verified":verified,"suggested_project_name":suggested_project,"github_app_install_url":install_url,"message":"Repository connected and readable." if verified else "Repository identified. Install/authorize the ETIS GitHub App or configure repository access, then verify again."}

@router.put("/teams/{team_id}/project")
def confirm_project(team_id:int,req:ConfirmProject,request:Request,db:Session=Depends(get_db)):
    ctx=require_authenticated(request)
    if ctx.get("role") not in STAFF_ROLES|{"developer"} and not db.query(TeamMembership).filter_by(team_id=team_id,user_id=ctx.get("uid")).first(): raise HTTPException(403,"Only a member of this team may confirm project metadata")
    team=db.get(Team,team_id)
    if not team: raise HTTPException(404,"Team not found")
    team.project_name=req.project_name.strip()
    if req.team_name: team.name=req.team_name.strip()
    db.commit(); return {"team_id":team.id,"team_name":team.name,"project_name":team.project_name}

@router.post("/teams/{team_id}/repository/verify")
def verify_repository(team_id:int,request:Request,db:Session=Depends(get_db)):
    ctx=require_authenticated(request)
    team=db.get(Team,team_id)
    if not team: raise HTTPException(404,"Team not found")
    if ctx.get("role") not in STAFF_ROLES|{"developer"}:
        if not db.query(TeamMembership).filter_by(team_id=team_id,user_id=ctx.get("uid")).first(): raise HTTPException(403,"Only a member of this team may verify its repository")
        if not db.query(GitHubIdentity).filter_by(user_id=ctx.get("uid")).first(): raise HTTPException(409,"Connect your GitHub identity before verifying the team repository")
    conn=db.query(RepositoryConnection).filter_by(team_id=team_id).first()
    if not conn: raise HTTPException(404,"No repository has been identified for this team")
    try:
        GitHubEvidenceProvider().head_sha(conn.repo_full_name)
    except Exception as e:
        raise HTTPException(502,f"Repository access is not ready: {e}") from e
    conn.status="verified"; conn.github_app_installed=bool(get_settings().github_app_id); conn.verified_at=datetime.now(timezone.utc); team.repo_full_name=conn.repo_full_name; db.commit()
    return {"verified":True,"repo_full_name":conn.repo_full_name,"status":conn.status}
