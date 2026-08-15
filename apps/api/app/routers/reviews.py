import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import EvidenceSnapshot, ReviewSession, ReviewTurn, Team, User
from ..schemas import ReviewStartRequest, ReviewResponseRequest
from ..services.challenge_engine import ChallengeEngine, Challenge
from ..services.evidence import GitHubEvidenceProvider
from ..services.seed import ensure_demo

router=APIRouter(prefix="/api/v1/reviews",tags=["reviews"])
engine=ChallengeEngine()


def _challenge_from_state(state: dict) -> Challenge:
    c=state["challenge"]
    return Challenge(**c)

@router.post("/start")
def start(req: ReviewStartRequest, db: Session=Depends(get_db)):
    student,demo_team=ensure_demo(db)
    team=db.get(Team,req.team_id) or demo_team
    user=db.get(User,req.user_id) if req.user_id else student
    if not user: user=student
    ev=GitHubEvidenceProvider().analyze(team.repo_full_name, req.phase_id)
    snap=EvidenceSnapshot(team_id=team.id,phase_id=req.phase_id,source="github" if ev.commit_sha!="demo-sha-001" else "demo",commit_sha=ev.commit_sha,summary_json=json.dumps(ev.to_dict()))
    db.add(snap); db.flush()
    challenge=engine.start(req.phase_id,ev,req.scenario_id)
    state={"challenge":challenge.to_dict(),"evidence_snapshot_id":snap.id,"evaluation":None}
    session=ReviewSession(team_id=team.id,user_id=user.id,phase_id=req.phase_id,mode=req.mode,scenario_id=req.scenario_id or "",challenge_state_json=json.dumps(state))
    db.add(session); db.flush()
    db.add(ReviewTurn(session_id=session.id,sequence=1,actor="reviewer",lens=challenge.lens,content=challenge.prompt,evidence_refs_json=json.dumps(challenge.evidence_refs),signals_json="{}"))
    db.commit(); db.refresh(session)
    return {"session_id":session.id,"team":{"id":team.id,"name":team.name,"project_name":team.project_name,"phase":req.phase_id},"challenge":challenge.to_dict(),"evidence":ev.to_dict()}

@router.get("/{session_id}")
def get_review(session_id:int,db:Session=Depends(get_db)):
    s=db.get(ReviewSession,session_id)
    if not s: raise HTTPException(404,"Review session not found")
    turns=db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    return {"session":{"id":s.id,"phase_id":s.phase_id,"status":s.status,"mode":s.mode},"state":json.loads(s.challenge_state_json),"turns":[{"sequence":t.sequence,"actor":t.actor,"lens":t.lens,"content":t.content,"evidence_refs":json.loads(t.evidence_refs_json)} for t in turns]}

@router.post("/{session_id}/respond")
def respond(session_id:int,req:ReviewResponseRequest,db:Session=Depends(get_db)):
    s=db.get(ReviewSession,session_id)
    if not s: raise HTTPException(404,"Review session not found")
    state=json.loads(s.challenge_state_json)
    challenge=_challenge_from_state(state)
    turns=db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    seq=(turns[-1].sequence if turns else 0)+1
    evaluation=engine.evaluate_response(challenge,req.response,req.evidence_refs,req.decision)
    db.add(ReviewTurn(session_id=session_id,sequence=seq,actor="student",lens="",content=req.response,evidence_refs_json=json.dumps(req.evidence_refs),signals_json=json.dumps(evaluation)))
    follow=engine.follow_up(challenge,req.response,evaluation)
    db.add(ReviewTurn(session_id=session_id,sequence=seq+1,actor="reviewer",lens=follow["lens"],content=follow["text"],evidence_refs_json="[]",signals_json=json.dumps({"provider":follow["provider"]})))
    state["evaluation"]=evaluation; state["last_follow_up"]=follow
    s.challenge_state_json=json.dumps(state)
    db.commit()
    return {"evaluation":evaluation,"follow_up":follow}
