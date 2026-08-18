from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db import SessionLocal, get_db

COOKIE_NAME="etis_session"

def _sign(payload: str) -> str:
    secret=get_settings().etis_session_secret.encode()
    return hmac.new(secret,payload.encode(),hashlib.sha256).hexdigest()

def _session_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token_for_session(token: str) -> str:
    """
    Derive a session-bound CSRF token without persisting another secret.

    The browser session credential remains HttpOnly. A safe derived value may
    be exposed separately to the authenticated UI and echoed in the
    X-CSRF-Token request header for cookie-authenticated mutations.
    """
    return _sign(f"csrf:{token}")


def validate_csrf_token(session_token: str, presented_token: str) -> bool:
    if not session_token or not presented_token:
        return False

    expected = csrf_token_for_session(session_token)
    return hmac.compare_digest(expected, presented_token)


def _as_utc(value: datetime) -> datetime:
    # SQLite may return timezone-aware columns as naive datetimes. Normalize
    # explicitly so test and PostgreSQL behavior use the same UTC semantics.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_session_token(
    user_id: int,
    login: str,
    role: str,
    ttl: int = 43200,
) -> str:
    """
    Issue an opaque, database-backed authentication session.

    `role` remains in the signature temporarily for compatibility with existing
    callers, but it is not stored in or trusted from the session credential.
    Authorization remains database-authoritative.
    """
    del role

    from ..models import AuthSession, User
    from .semester_lifecycle import (
        active_student_enrollments,
        valid_staff_assignments,
    )

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="Cannot create a session for an inactive user",
            )

        has_active_enrollment = bool(
            active_student_enrollments(db, user_id)
        )
        has_valid_staff = bool(
            valid_staff_assignments(db, user_id)
        )

        requires_course_authorization = (
            has_active_enrollment or has_valid_staff
        )

        # Production authentication must always correspond to current course
        # authorization. Development-only sessions remain available for local
        # deterministic fixtures that intentionally do not model a full roster.
        if (
            not requires_course_authorization
            and get_settings().etis_env != "development"
        ):
            raise HTTPException(
                status_code=401,
                detail="Engineering Studio authorization is not active",
            )

        row = AuthSession(
            user_id=user_id,
            token_hash=_session_token_hash(token),
            login=login,
            requires_course_authorization=requires_course_authorization,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    return token


def parse_session_token(token: str) -> dict:
    from ..models import AuthSession, User
    from .semester_lifecycle import (
        active_student_enrollments,
        valid_staff_assignments,
    )

    token_hash = _session_token_hash(token)
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        row = (
            db.query(AuthSession)
            .filter_by(token_hash=token_hash)
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        if row.revoked_at is not None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        if _as_utc(row.expires_at) <= now:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        user = db.get(User, row.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        staff_rows = valid_staff_assignments(db, user.id)
        active_enrollment = bool(
            active_student_enrollments(db, user.id)
        )

        # Sessions issued under real course authorization remain valid only
        # while lifecycle-valid authorization still exists. Archiving a term
        # removes student authorization immediately; only Course Owner and
        # Instructor assignments remain eligible for historical read access.
        if (
            row.requires_course_authorization
            and not active_enrollment
            and not staff_rows
        ):
            row.revoked_at = now
            db.commit()

            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        # An unbound session is a development-only compatibility mechanism.
        # It must never become a valid production authentication path.
        if (
            not row.requires_course_authorization
            and get_settings().etis_env != "development"
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        current_staff_role = highest_staff_role(
            [staff.staff_role for staff in staff_rows]
        )

        if row.requires_course_authorization:
            current_role = current_staff_role or "student"
        else:
            current_role = user.role or "student"

        return {
            "uid": user.id,
            "login": row.login,
            "role": current_role,
            "sid": row.id,
            "exp": int(_as_utc(row.expires_at).timestamp()),
        }
    finally:
        db.close()


def request_session_token(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token

    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    return None


def revoke_session_token(token: str, db: Session) -> bool:
    from ..models import AuthSession

    row = (
        db.query(AuthSession)
        .filter_by(token_hash=_session_token_hash(token))
        .first()
    )

    if not row:
        return False

    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()

    return True

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
    token = request_session_token(request)
    if not token:
        return None

    try:
        return parse_session_token(token)
    except HTTPException:
        return None

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

def resolve_entra_identity(claims: dict) -> dict:
    """
    Resolve a verified Microsoft Entra identity into the canonical Studio
    identity admitted at the authentication boundary.

    Normal students must use the configured institutional domain.

    A production-acceptance test student may be admitted only when the verified
    tenant-scoped Entra Object ID (oid) exactly matches the configured test
    principal. The configured test email is then used as the canonical Studio
    identity. This never permits an external email domain generally.
    """
    s = get_settings()

    oid = str(claims.get("oid") or "").strip()
    if not oid:
        raise HTTPException(
            status_code=401,
            detail="Microsoft identity is missing its object identifier",
        )

    configured_test_oid = str(
        s.etis_production_test_student_oid or ""
    ).strip()
    configured_test_email = str(
        s.etis_production_test_student_email or ""
    ).strip().lower()

    if configured_test_oid and oid.casefold() == configured_test_oid.casefold():
        if not configured_test_email:
            raise HTTPException(
                status_code=403,
                detail="Production test student identity is not fully configured",
            )
        return {
            "oid": oid,
            "email": configured_test_email,
            "is_production_test_student": True,
        }

    email = str(
        claims.get("preferred_username")
        or claims.get("email")
        or ""
    ).strip().lower()

    allowed_domain = str(s.entra_allowed_domain or "").strip().lower()
    if (
        not email
        or not allowed_domain
        or not email.endswith("@" + allowed_domain)
    ):
        raise HTTPException(
            status_code=403,
            detail="Use your authorized Loyola account",
        )

    return {
        "oid": oid,
        "email": email,
        "is_production_test_student": False,
    }


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
    tid=str(unverified.get("tid") or "").strip()
    if not tid:
        raise HTTPException(401,"Microsoft identity is missing tenant information")

    configured_tenant=str(s.entra_tenant or "").strip()
    if not configured_tenant or tid.casefold()!=configured_tenant.casefold():
        raise HTTPException(
            status_code=403,
            detail="Microsoft identity tenant is not authorized",
        )

    issuer=f"https://login.microsoftonline.com/{configured_tenant}/v2.0"
    jwk=PyJWKClient("https://login.microsoftonline.com/common/discovery/v2.0/keys").get_signing_key_from_jwt(id_token)
    claims=jwt.decode(id_token,jwk.key,algorithms=["RS256"],audience=s.entra_client_id,issuer=issuer)

    verified_tid=str(claims.get("tid") or "").strip()
    if not verified_tid or verified_tid.casefold()!=configured_tenant.casefold():
        raise HTTPException(
            status_code=403,
            detail="Microsoft identity tenant is not authorized",
        )

    if expected_nonce and claims.get("nonce")!=expected_nonce: raise HTTPException(401,"Microsoft sign-in nonce did not match")
    return claims

STAFF_ROLES={"course_owner","instructor","ta","reviewer"}
STAFF_RANK={"reviewer":1,"ta":2,"instructor":3,"course_owner":4}

def auth_context(request: Request) -> dict:
    s = get_settings()

    # A presented credential is an explicit authentication attempt. It must
    # either resolve successfully or fail with 401. Never collapse an invalid,
    # expired, or revoked credential into "no identity" and then upgrade the
    # request to development's privileged developer context.
    token = request_session_token(request)
    if token:
        return parse_session_token(token)

    # The developer fallback exists only for requests that present no
    # authentication credential at all.
    if s.etis_env == "development" and s.etis_dev_login:
        return {
            "uid": None,
            "login": "development",
            "role": "developer",
        }

    raise HTTPException(
        status_code=401,
        detail="Sign in with Loyola to continue",
    )

def require_authenticated(request: Request) -> dict:
    return auth_context(request)

def require_staff(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    ctx = auth_context(request)

    if ctx.get("role") == "developer":
        return ctx

    user_id = ctx.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=403,
            detail="Teaching-staff authorization is required",
        )

    from ..models import User
    from .semester_lifecycle import valid_staff_assignments

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Teaching-staff authorization is required",
        )

    assignments = valid_staff_assignments(db, user_id)

    current_role = highest_staff_role(
        [assignment.staff_role for assignment in assignments]
    )
    if not current_role:
        raise HTTPException(
            status_code=403,
            detail="Teaching-staff authorization is required",
        )

    # Do not propagate stale role authority from the signed session. Return a
    # normalized context whose staff role reflects current database state.
    current_ctx = dict(ctx)
    current_ctx["role"] = current_role
    return current_ctx

def highest_staff_role(roles) -> str|None:
    values=[r for r in roles if r in STAFF_RANK]
    return max(values,key=lambda r:STAFF_RANK[r]) if values else None

def section_staff_role(db, user_id:int|None, section_id:int) -> str|None:
    from .semester_lifecycle import staff_role_for_section
    return staff_role_for_section(db, user_id, section_id)

def accessible_section_ids(db, ctx:dict) -> set[int]|None:
    """Return None for development's unrestricted identity, else lifecycle-valid staff sections."""
    if ctx.get("role")=="developer": return None
    uid=ctx.get("uid")
    if not uid: return set()
    from .semester_lifecycle import accessible_staff_section_ids
    return accessible_staff_section_ids(db, uid)

def require_course_owner_ctx(db, ctx:dict) -> dict:
    if ctx.get("role")=="developer": return ctx
    uid=ctx.get("uid")
    from .semester_lifecycle import has_course_owner_assignment
    if has_course_owner_assignment(db, uid): return ctx
    raise HTTPException(403,"Course Owner authorization is required")

def require_section_role(db,ctx:dict,section_id:int,allowed:set[str]) -> str:
    if ctx.get("role")=="developer": return "developer"
    role=section_staff_role(db,ctx.get("uid"),section_id)
    if role and role in allowed: return role
    raise HTTPException(403,"You do not have the required authorization for this section")


TEAM_READ_STAFF_ROLES = {"course_owner", "instructor", "ta", "reviewer"}


def require_team_access(db, ctx: dict, team_id: int):
    """
    Resolve an active team only when the authenticated identity is authorized
    to access it under the current semester lifecycle.

    Access is granted to:
    - the local developer identity in development;
    - an active student who is a member of the team and remains actively
      enrolled in the team's active term;
    - lifecycle-valid teaching staff assigned to the team's section.

    Archived Course Owner and Instructor assignments retain read-only team
    access. Archived TA/Reviewer assignments and archived student enrollments
    do not grant access.

    Missing and unauthorized teams deliberately produce the same 404 response
    so callers cannot use the API to enumerate protected teams.
    """
    from ..models import (
        Team,
        TeamMembership,
        TeamSection,
        User,
    )
    from .semester_lifecycle import (
        staff_role_for_section,
        student_has_active_section_access,
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
        # deterministic development compatibility for those fixtures.
        if team_section and not student_has_active_section_access(
            db,
            user_id,
            team_section.section_id,
        ):
            raise HTTPException(status_code=404, detail="Team not found")
        return team

    if team_section:
        role = staff_role_for_section(
            db,
            user_id,
            team_section.section_id,
        )
        if role in TEAM_READ_STAFF_ROLES:
            return team

    raise HTTPException(status_code=404, detail="Team not found")
