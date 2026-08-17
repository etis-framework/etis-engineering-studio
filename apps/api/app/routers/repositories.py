from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..schemas import RepoAnalyzeRequest
from ..services.evidence import GitHubEvidenceProvider
from ..services.auth import require_authenticated, require_team_access

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])

@router.post("/analyze")
def analyze(
    req: RepoAnalyzeRequest,
    db: Session = Depends(get_db),
    ctx: dict = Depends(require_authenticated),
):
    team = require_team_access(db, ctx, req.team_id)

    authoritative_repo = (team.repo_full_name or "").strip()
    if not authoritative_repo:
        raise HTTPException(
            status_code=409,
            detail="Team repository is not configured",
        )

    requested_repo = (req.repo_full_name or "").strip()
    if requested_repo and requested_repo.casefold() != authoritative_repo.casefold():
        raise HTTPException(
            status_code=409,
            detail="Repository does not match the team's configured repository",
        )

    try:
        result = GitHubEvidenceProvider().analyze(
            authoritative_repo,
            req.phase_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return result.to_dict()
