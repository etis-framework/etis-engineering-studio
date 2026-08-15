import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Team, User, TeamMembership, ReviewSession, ReviewTurn
from ..services.seed import ensure_demo

router=APIRouter(prefix="/api/v1/instructor",tags=["instructor"])

@router.get("/overview")
def overview(db:Session=Depends(get_db)):
    ensure_demo(db)
    teams=db.query(Team).filter_by(is_active=True).all()
    out=[]
    for t in teams:
        sessions=db.query(ReviewSession).filter_by(team_id=t.id).all()
        members=db.query(TeamMembership).filter_by(team_id=t.id).all()
        out.append({
            "id":t.id,"team_key":t.team_key,"name":t.name,"project":t.project_name,"phase":t.current_phase,"repo":t.repo_full_name,
            "members":len(members),"review_sessions":len(sessions),"active_sessions":sum(s.status=="active" for s in sessions),
            "last_activity":max([s.started_at.isoformat() for s in sessions],default=None)
        })
    return {"course_namespace":"COMP330-F26","teams":out,"principle":"Instructor analytics support judgment; they do not reduce contribution to commit counts or lines of code."}
