from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Team, TeamMembership, User
from ..schemas import DevLoginRequest
from ..services.auth import create_session_token
from ..services.seed import ensure_demo


router = APIRouter(prefix="/api/v1/dev", tags=["development"])


def _require_dev_mode():
    settings = get_settings()
    if settings.etis_env != "development" or not settings.etis_dev_login:
        raise HTTPException(status_code=404)
    return settings


@router.post("/login")
def login(req: DevLoginRequest, db: Session = Depends(get_db)):
    settings = _require_dev_mode()

    demo_user, demo_team = ensure_demo(db)

    user = db.query(User).filter_by(github_login=req.github_login).first()
    if not user:
        user = User(
            github_login=req.github_login,
            display_name=req.display_name,
            role=req.role,
        )
        db.add(user)
        db.flush()

    team = (
        db.query(Team)
        .filter_by(
            course_namespace=settings.etis_course_namespace,
            team_key=req.team_key,
        )
        .first()
        or demo_team
    )

    if not db.query(TeamMembership).filter_by(
        team_id=team.id,
        user_id=user.id,
    ).first():
        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
            )
        )
        db.commit()

    token = create_session_token(
        user.id,
        user.github_login,
        user.role,
    )

    return {
        "token": token,
        "user": {
            "id": user.id,
            "github_login": user.github_login,
            "display_name": user.display_name,
            "role": user.role,
        },
        "team": {
            "id": team.id,
            "name": team.name,
            "phase": team.current_phase,
        },
    }


@router.post("/seed")
def seed(db: Session = Depends(get_db)):
    _require_dev_mode()

    user, team = ensure_demo(db)

    return {
        "user_id": user.id,
        "team_id": team.id,
    }
