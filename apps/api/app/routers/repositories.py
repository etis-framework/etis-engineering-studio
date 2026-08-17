from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Team
from ..schemas import RepoAnalyzeRequest
from ..services.evidence import GitHubEvidenceProvider

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])

@router.post("/analyze")
def analyze(req: RepoAnalyzeRequest, db: Session = Depends(get_db)):
    team = db.get(Team, req.team_id)
    repo = (req.repo_full_name or (team.repo_full_name if team else "") or "").strip()
    try:
        result = GitHubEvidenceProvider().analyze(repo, req.phase_id)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    if team and req.repo_full_name:
        team.repo_full_name = req.repo_full_name.strip()
        db.commit()
    return result.to_dict()
