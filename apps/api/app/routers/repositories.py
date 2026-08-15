from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Team
from ..schemas import RepoAnalyzeRequest
from ..services.evidence import GitHubEvidenceProvider

router=APIRouter(prefix="/api/v1/repositories",tags=["repositories"])

@router.post("/analyze")
def analyze(req:RepoAnalyzeRequest,db:Session=Depends(get_db)):
    team=db.get(Team,req.team_id)
    repo=req.repo_full_name or (team.repo_full_name if team else "demo/comp330-f26-team-01")
    return GitHubEvidenceProvider().analyze(repo,req.phase_id).to_dict()
