import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..db import get_db
from ..config import get_settings
from ..models import User
from ..services.auth import github_authorize_url, github_exchange, create_session_token

router=APIRouter(prefix="/auth",tags=["auth"])
_state_store=set()

@router.get("/github")
def github_login():
    s=get_settings()
    if not s.github_oauth_client_id: raise HTTPException(503,"GitHub OAuth is not configured")
    state=secrets.token_urlsafe(24); _state_store.add(state)
    return RedirectResponse(github_authorize_url(state))

@router.get("/github/callback")
def github_callback(code:str,state:str,db:Session=Depends(get_db)):
    if state not in _state_store: raise HTTPException(400,"Invalid OAuth state")
    _state_store.discard(state)
    profile=github_exchange(code); login=profile["login"]
    user=db.query(User).filter_by(github_login=login).first()
    if not user:
        # Production policy: un-enrolled users are not automatically admitted.
        raise HTTPException(403,"This GitHub identity is not enrolled in the active course namespace")
    token=create_session_token(user.id,user.github_login,user.role)
    return RedirectResponse(url=f"/?session={token}")
