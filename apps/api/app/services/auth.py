from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from urllib.parse import urlencode
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request
from ..config import get_settings

COOKIE_NAME="etis_session"

def _sign(payload: str) -> str:
    secret=get_settings().etis_session_secret.encode()
    return hmac.new(secret,payload.encode(),hashlib.sha256).hexdigest()

def create_session_token(user_id: int, login: str, role: str, ttl=43200) -> str:
    data={"uid":user_id,"login":login,"role":role,"exp":int(time.time())+ttl,"nonce":secrets.token_hex(6)}
    raw=base64.urlsafe_b64encode(json.dumps(data,separators=(",",":")).encode()).decode().rstrip("=")
    return f"{raw}.{_sign(raw)}"

def parse_session_token(token: str) -> dict:
    try:
        raw,sig=token.rsplit(".",1)
        if not hmac.compare_digest(_sign(raw),sig): raise ValueError("bad signature")
        padded=raw+"="*((4-len(raw)%4)%4)
        data=json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(data["exp"])<int(time.time()): raise ValueError("expired")
        return data
    except Exception as e:
        raise HTTPException(status_code=401,detail="Invalid or expired session") from e

def create_flow_state(kind:str, payload:dict|None=None, ttl:int=600) -> str:
    """Stateless, signed OAuth/OIDC flow state suitable for multiple app replicas."""
    data={"kind":kind,"exp":int(time.time())+ttl,"nonce":secrets.token_urlsafe(18),**(payload or {})}
    raw=base64.urlsafe_b64encode(json.dumps(data,separators=(",",":"),sort_keys=True).encode()).decode().rstrip("=")
    return f"{raw}.{_sign(raw)}"

def parse_flow_state(token:str, expected_kind:str) -> dict:
    try:
        raw,sig=token.rsplit(".",1)
        if not hmac.compare_digest(_sign(raw),sig): raise ValueError("bad signature")
        padded=raw+"="*((4-len(raw)%4)%4)
        data=json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(data.get("exp",0))<int(time.time()): raise ValueError("expired")
        if data.get("kind")!=expected_kind: raise ValueError("wrong flow")
        return data
    except Exception as e:
        raise HTTPException(status_code=400,detail="Invalid or expired authorization state") from e

def request_identity(request: Request) -> dict|None:
    token=request.cookies.get(COOKIE_NAME)
    if not token:
        auth=request.headers.get("Authorization","")
        if auth.lower().startswith("bearer "): token=auth.split(" ",1)[1].strip()
    if not token: return None
    try: return parse_session_token(token)
    except HTTPException: return None

def github_authorize_url(state: str) -> str:
    s=get_settings(); q=urlencode({"client_id":s.github_oauth_client_id,"redirect_uri":s.github_oauth_redirect_uri,"scope":"read:user user:email","state":state})
    return f"https://github.com/login/oauth/authorize?{q}"

def github_exchange(code: str) -> dict:
    s=get_settings()
    with httpx.Client(timeout=20) as c:
        t=c.post("https://github.com/login/oauth/access_token",headers={"Accept":"application/json"},data={"client_id":s.github_oauth_client_id,"client_secret":s.github_oauth_client_secret,"code":code,"redirect_uri":s.github_oauth_redirect_uri})
        t.raise_for_status(); token=t.json().get("access_token")
        if not token: raise HTTPException(401,"GitHub OAuth exchange failed")
        u=c.get("https://api.github.com/user",headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"}); u.raise_for_status(); return u.json()

def entra_authorize_url(state:str,nonce:str) -> str:
    s=get_settings(); q=urlencode({"client_id":s.entra_client_id,"response_type":"code","redirect_uri":s.entra_redirect_uri,"response_mode":"query","scope":"openid profile email","state":state,"nonce":nonce,"prompt":"select_account"})
    return f"https://login.microsoftonline.com/{s.entra_tenant}/oauth2/v2.0/authorize?{q}"

def entra_exchange(code:str,expected_nonce:str) -> dict:
    s=get_settings(); token_url=f"https://login.microsoftonline.com/{s.entra_tenant}/oauth2/v2.0/token"
    with httpx.Client(timeout=25) as c:
        r=c.post(token_url,data={"client_id":s.entra_client_id,"client_secret":s.entra_client_secret,"grant_type":"authorization_code","code":code,"redirect_uri":s.entra_redirect_uri,"scope":"openid profile email"}); r.raise_for_status(); payload=r.json()
    id_token=payload.get("id_token")
    if not id_token: raise HTTPException(401,"Microsoft sign-in did not return an identity token")
    unverified=jwt.decode(id_token,options={"verify_signature":False,"verify_aud":False})
    tid=unverified.get("tid")
    if not tid: raise HTTPException(401,"Microsoft identity is missing tenant information")
    issuer=f"https://login.microsoftonline.com/{tid}/v2.0"
    jwk=PyJWKClient("https://login.microsoftonline.com/common/discovery/v2.0/keys").get_signing_key_from_jwt(id_token)
    claims=jwt.decode(id_token,jwk.key,algorithms=["RS256"],audience=s.entra_client_id,issuer=issuer)
    if expected_nonce and claims.get("nonce")!=expected_nonce: raise HTTPException(401,"Microsoft sign-in nonce did not match")
    email=(claims.get("preferred_username") or claims.get("email") or "").lower()
    if not email.endswith("@"+s.entra_allowed_domain.lower()): raise HTTPException(403,"Use your authorized Loyola account")
    return claims

STAFF_ROLES={"course_owner","instructor","ta","reviewer"}
STAFF_RANK={"reviewer":1,"ta":2,"instructor":3,"course_owner":4}

def auth_context(request: Request) -> dict:
    s=get_settings()
    ident=request_identity(request)
    if ident:
        return ident
    if s.etis_env=="development" and s.etis_dev_login:
        return {"uid":None,"login":"development","role":"developer"}
    raise HTTPException(401,"Sign in with Loyola to continue")

def require_authenticated(request: Request) -> dict:
    return auth_context(request)

def require_staff(request: Request) -> dict:
    ctx=auth_context(request)
    if ctx.get("role")=="developer" or ctx.get("role") in STAFF_ROLES:
        return ctx
    raise HTTPException(403,"Teaching-staff authorization is required")

def highest_staff_role(roles) -> str|None:
    values=[r for r in roles if r in STAFF_RANK]
    return max(values,key=lambda r:STAFF_RANK[r]) if values else None

def section_staff_role(db, user_id:int|None, section_id:int) -> str|None:
    if not user_id: return None
    from ..models import SectionStaff
    rows=db.query(SectionStaff).filter_by(section_id=section_id,user_id=user_id,is_active=True).all()
    return highest_staff_role([r.staff_role for r in rows])

def accessible_section_ids(db, ctx:dict) -> set[int]|None:
    """Return None for unrestricted developer/course-owner access, else assigned sections."""
    if ctx.get("role")=="developer": return None
    uid=ctx.get("uid")
    if not uid: return set()
    from ..models import SectionStaff
    rows=db.query(SectionStaff).filter_by(user_id=uid,is_active=True).all()
    if any(r.staff_role=="course_owner" for r in rows): return None
    return {r.section_id for r in rows}

def require_course_owner_ctx(db, ctx:dict) -> dict:
    if ctx.get("role")=="developer": return ctx
    uid=ctx.get("uid")
    from ..models import SectionStaff
    if uid and db.query(SectionStaff).filter_by(user_id=uid,staff_role="course_owner",is_active=True).first(): return ctx
    raise HTTPException(403,"Course Owner authorization is required")

def require_section_role(db,ctx:dict,section_id:int,allowed:set[str]) -> str:
    if ctx.get("role")=="developer": return "developer"
    role=section_staff_role(db,ctx.get("uid"),section_id)
    if role and role in allowed: return role
    # A course owner assignment is intentionally global across the term/application course context.
    if ctx.get("uid"):
        from ..models import SectionStaff
        if db.query(SectionStaff).filter_by(user_id=ctx["uid"],staff_role="course_owner",is_active=True).first(): return "course_owner"
    raise HTTPException(403,"You do not have the required authorization for this section")


TEAM_READ_STAFF_ROLES = {"course_owner", "instructor", "ta", "reviewer"}


def require_team_access(db, ctx: dict, team_id: int):
    """
    Resolve an active team only when the authenticated identity is authorized
    to access it.

    Authorization is derived from current database state rather than trusting
    the role embedded in the session token.

    Access is granted to:
    - the local developer identity in development;
    - an active student who is a member of the team and, when the team is
      section-bound, remains actively enrolled in that section;
    - an active course owner;
    - active teaching staff assigned to the team's section.

    Missing and unauthorized teams deliberately produce the same 404 response
    so callers cannot use the API to enumerate protected teams.
    """
    from ..models import (
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamMembership,
        TeamSection,
        User,
    )

    team = db.get(Team, team_id)
    if not team or not team.is_active:
        raise HTTPException(status_code=404, detail="Team not found")

    if ctx.get("role") == "developer":
        return team

    user_id = ctx.get("uid")
    if not user_id:
        raise HTTPException(status_code=404, detail="Team not found")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="Team not found")

    # Course Owner is intentionally global across the course context.
    course_owner = (
        db.query(SectionStaff)
        .filter_by(
            user_id=user_id,
            staff_role="course_owner",
            is_active=True,
        )
        .first()
    )
    if course_owner:
        return team

    team_section = (
        db.query(TeamSection)
        .filter_by(team_id=team.id)
        .first()
    )

    membership = (
        db.query(TeamMembership)
        .filter_by(team_id=team.id, user_id=user_id)
        .first()
    )

    if membership:
        # Older/local fixture teams may not yet be section-bound. Preserve
        # that deterministic development behavior. Once section-bound,
        # enrollment must still be active.
        if team_section:
            enrollment = (
                db.query(SectionEnrollment)
                .filter_by(
                    section_id=team_section.section_id,
                    user_id=user_id,
                    status="active",
                )
                .first()
            )
            if not enrollment:
                raise HTTPException(status_code=404, detail="Team not found")
        return team

    if team_section:
        staff_rows = (
            db.query(SectionStaff)
            .filter_by(
                section_id=team_section.section_id,
                user_id=user_id,
                is_active=True,
            )
            .all()
        )
        if any(row.staff_role in TEAM_READ_STAFF_ROLES for row in staff_rows):
            return team

    raise HTTPException(status_code=404, detail="Team not found")
