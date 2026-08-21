from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..db import get_db
from ..config import get_settings
from ..models import User, InstitutionalIdentity, SectionEnrollment, GitHubIdentity, SectionStaff
from ..services.auth import (github_authorize_url, github_exchange, entra_authorize_url, entra_exchange, resolve_entra_identity,
    create_session_token, request_identity, auth_context, COOKIE_NAME, highest_staff_role,
    create_flow_state, parse_flow_state, request_session_token,
    revoke_session_token, csrf_token_for_session)
from ..services.course_admin import ensure_term, ensure_section, generate_schedule

router=APIRouter(prefix="/auth",tags=["auth"])

def _set_session(response:RedirectResponse,user:User,login:str):
    token=create_session_token(user.id,login,user.role)
    response.set_cookie(COOKIE_NAME,token,httponly=True,secure=get_settings().etis_env!="development",samesite="lax",max_age=43200,path="/")

@router.get("/entra")
def entra_login():
    s=get_settings()
    if not s.entra_client_id or not s.entra_client_secret: raise HTTPException(503,"Loyola Microsoft SSO is not configured")
    state=create_flow_state("entra")
    flow=parse_flow_state(state,"entra")
    return RedirectResponse(entra_authorize_url(state,flow["nonce"]))

@router.get("/entra/callback")
def entra_callback(code:str,state:str,db:Session=Depends(get_db)):
    pending=parse_flow_state(state,"entra")
    claims=entra_exchange(code,pending.get("nonce",""))
    resolved=resolve_entra_identity(claims)
    email=resolved["email"]
    oid=resolved["oid"]
    production_test_student=resolved["is_production_test_student"]
    s=get_settings()
    sid=(
        s.etis_production_test_student_id.strip().lower()
        if production_test_student and s.etis_production_test_student_id.strip()
        else email.split("@",1)[0]
    )
    oid_matches = db.query(InstitutionalIdentity).filter(
        InstitutionalIdentity.provider_subject == oid
    ).all()
    if len(oid_matches) > 1:
        raise HTTPException(
            409,
            "Microsoft Entra identity is bound to more than one Studio identity",
        )

    ident = oid_matches[0] if oid_matches else None

    if not ident:
        roster_matches = db.query(InstitutionalIdentity).filter(
            (InstitutionalIdentity.institutional_email == email)
            | (InstitutionalIdentity.student_id == sid)
        ).all()

        if len(roster_matches) > 1:
            raise HTTPException(
                409,
                "Institutional roster identity is ambiguous",
            )

        ident = roster_matches[0] if roster_matches else None

        if (
            ident
            and ident.provider_subject
            and ident.provider_subject.casefold() != oid.casefold()
        ):
            raise HTTPException(
                409,
                "This institutional identity is already bound to a different "
                "Microsoft Entra account",
            )
    if not ident and s.etis_bootstrap_owner_email and email==s.etis_bootstrap_owner_email.lower():
        user=User(github_login=f"staff:{email}",display_name=claims.get("name") or email.split("@")[0],role="instructor")
        db.add(user); db.flush(); ident=InstitutionalIdentity(user_id=user.id,student_id=f"staff:{sid}",institutional_email=email,provider_subject=oid); db.add(ident); db.flush()
        term=ensure_term(db,s.etis_course_namespace); section=ensure_section(db,term); generate_schedule(db,section,term.starts_on or "2026-08-25")
        db.add(SectionStaff(section_id=section.id,user_id=user.id,staff_role="course_owner",is_active=True)); db.commit()
    if not ident: raise HTTPException(403,"This Loyola identity is not on an active Engineering Studio roster or teaching-staff list")
    active=db.query(SectionEnrollment).filter_by(user_id=ident.user_id,status="active").first()
    staff_rows=db.query(SectionStaff).filter_by(user_id=ident.user_id,is_active=True).all()
    if not active and not staff_rows: raise HTTPException(403,"Your Engineering Studio authorization is not active")
    user=db.get(User,ident.user_id)
    effective_role=highest_staff_role([x.staff_role for x in staff_rows]) or "student"
    user.role="instructor" if effective_role in {"course_owner","instructor"} else effective_role
    ident.provider_subject=oid
    from datetime import datetime,timezone
    ident.last_verified_at=datetime.now(timezone.utc)
    db.commit()
    response=RedirectResponse("/")
    _set_session(response,user,email)
    return response

@router.get("/github/link")
def github_link(request:Request):
    ident=request_identity(request)
    if not ident: raise HTTPException(401,"Sign in with Loyola before connecting GitHub")
    s=get_settings()
    if not s.github_oauth_client_id: raise HTTPException(503,"GitHub identity linking is not configured")
    state=create_flow_state(
        "github-link",
        {"user_id":ident["uid"], "session_id":ident["sid"]},
    )
    return RedirectResponse(github_authorize_url(state))

@router.get("/github/callback")
def github_callback(
    code:str,
    state:str,
    request:Request,
    db:Session=Depends(get_db),
):
    pending=parse_flow_state(state,"github-link")

    # Signed OAuth state identifies the flow, but it is not authentication.
    # Require the still-valid, revocation-aware Studio session that initiated
    # the link and bind the callback to that same Studio user before exchanging
    # the GitHub code or mutating identity state.
    studio_identity=auth_context(request)
    if studio_identity.get("role") == "developer":
        raise HTTPException(403,"GitHub identity linking requires a Studio user session")

    state_user_id=pending.get("user_id")
    state_session_id=pending.get("session_id")
    if (
        not state_user_id
        or not state_session_id
        or studio_identity.get("uid") != state_user_id
        or studio_identity.get("sid") != state_session_id
    ):
        raise HTTPException(403,"GitHub authorization does not match the initiating Studio session")

    profile=github_exchange(code)

    login=str(profile.get("login") or "").strip()
    github_user_id=str(profile.get("id") or "").strip()

    if not login or not github_user_id:
        raise HTTPException(
            401,
            "GitHub identity response was incomplete",
        )

    if pending.get("kind")=="github-link":
        user_id=pending["user_id"]

        # GitHub login names can change. The immutable GitHub account ID is
        # therefore part of the authorization boundary, not display data.
        conflict=(
            db.query(GitHubIdentity)
            .filter(
                or_(
                    func.lower(GitHubIdentity.github_login)
                    == login.casefold(),
                    GitHubIdentity.github_user_id == github_user_id,
                )
            )
            .first()
        )

        if conflict and conflict.user_id!=user_id:
            raise HTTPException(
                409,
                "That GitHub identity is already linked to another Studio user",
            )

        link=(
            db.query(GitHubIdentity)
            .filter_by(user_id=user_id)
            .first()
        )

        if not link:
            link=GitHubIdentity(
                user_id=user_id,
                github_login=login,
                github_user_id=github_user_id,
            )
            db.add(link)
        else:
            # Legitimate rename of the same GitHub account.
            link.github_login=login
            link.github_user_id=github_user_id

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                409,
                "That GitHub identity is already linked to another Studio user",
            ) from exc

        return RedirectResponse("/?github=linked")

    raise HTTPException(400,"Unsupported GitHub authorization flow")

@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    token = request_session_token(request)
    if token:
        revoke_session_token(token, db)

    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response

@router.get("/me")
def me(request:Request,response:Response,db:Session=Depends(get_db)):
    # Authentication/bootstrap state, including the browser CSRF token, must
    # never be stored by browsers or intermediary caches.
    response.headers["Cache-Control"]="no-store"

    ident=request_identity(request)
    if not ident:
        return {"authenticated":False}

    user=db.get(User,ident["uid"])
    if not user:
        return {"authenticated":False}

    institutional=db.query(InstitutionalIdentity).filter_by(user_id=user.id).first()
    gh=db.query(GitHubIdentity).filter_by(user_id=user.id).first()
    staff_rows=db.query(SectionStaff).filter_by(user_id=user.id,is_active=True).all()
    assignments=[{"section_id":x.section_id,"role":x.staff_role} for x in staff_rows]
    role=highest_staff_role([x.staff_role for x in staff_rows]) or ident.get("role") or "student"

    body={
        "authenticated":True,
        "user":{
            "id":user.id,
            "display_name":user.display_name,
            "role":role,
            "email":institutional.institutional_email if institutional else None,
            "student_id":institutional.student_id if institutional else None,
            "github_login":gh.github_login if gh else None,
            "staff_assignments":assignments,
        },
    }

    # CSRF protection is required only for browser cookie authentication.
    # Bearer-only API clients remain outside the browser CSRF threat model.
    cookie_token=request.cookies.get(COOKIE_NAME)
    if cookie_token:
        body["csrf_token"]=csrf_token_for_session(cookie_token)

    return body
