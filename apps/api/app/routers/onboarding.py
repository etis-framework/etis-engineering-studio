from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..config import get_settings
from ..models import (
    User,
    Team,
    TeamMembership,
    TeamSection,
    CourseSection,
    InstitutionalIdentity,
    GitHubIdentity,
    RepositoryConnection,
    REPOSITORY_STATUS_CANDIDATE,
    REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED,
    REPOSITORY_STATUS_VERIFIED,
    REPOSITORY_OWNER_USER,
    REPOSITORY_OWNER_ORGANIZATION,
)
from ..services.course_admin import phase_access, repo_name_from_clone
from ..services.auth import (
    STAFF_ROLES,
    accessible_section_ids,
    require_authenticated,
    require_section_role,
    require_team_access,
)
from ..services.semester_lifecycle import (
    active_student_enrollments,
    active_student_section_ids,
    require_team_mutable,
)
from ..services.evidence import GitHubEvidenceProvider
from ..services.github_app import (
    GitHubOwnerResolutionError,
    repository_owner_identity,
)
from ..services.repository_policy import (
    COMP330_STARTER_KIT_REPOSITORY,
    is_comp330_starter_kit,
    is_configured_production_test_email,
)

router=APIRouter(prefix="/api/v1/onboarding",tags=["onboarding"])

class ConnectRepository(BaseModel):
    clone_url:str=Field(min_length=10,max_length=500)
    user_id:int|None=None

class ConfirmProject(BaseModel):
    project_name:str=Field(min_length=2,max_length=200)
    team_name:str|None=Field(default=None,max_length=200)


TEAM_CONFIGURATION_STAFF_ROLES = {"course_owner", "instructor"}


def _github_identity_complete(identity: GitHubIdentity | None) -> bool:
    return bool(
        identity
        and str(identity.github_login or "").strip()
        and str(identity.github_user_id or "").strip()
    )


def _team_section_link(db: Session, team_id: int) -> TeamSection | None:
    return db.query(TeamSection).filter_by(team_id=team_id).first()


def _require_team_configuration_actor(
    db: Session,
    ctx: dict,
    team: Team,
) -> None:
    """Allow active team members or current Course Owner/Instructor staff.

    Team-read authority is intentionally broader than configuration authority.
    TA/Reviewer access remains read-oriented and cannot silently become
    repository/project mutation authority.
    """
    if ctx.get("role") == "developer":
        return

    user_id = ctx.get("uid")
    if user_id and db.query(TeamMembership).filter_by(
        team_id=team.id,
        user_id=user_id,
    ).first():
        return

    section_link = _team_section_link(db, team.id)
    if not section_link:
        raise HTTPException(403, "Team configuration authorization is required")

    require_section_role(
        db,
        ctx,
        section_link.section_id,
        TEAM_CONFIGURATION_STAFF_ROLES,
    )


def _require_repository_recovery_actor(
    db: Session,
    ctx: dict,
    team: Team,
) -> None:
    if ctx.get("role") == "developer":
        return

    section_link = _team_section_link(db, team.id)
    if not section_link:
        raise HTTPException(403, "Repository recovery authorization is required")

    require_section_role(
        db,
        ctx,
        section_link.section_id,
        TEAM_CONFIGURATION_STAFF_ROLES,
    )


def _require_personal_repository_owner(
    db: Session,
    ctx: dict,
    conn: RepositoryConnection,
) -> None:
    if ctx.get("role") == "developer":
        return

    actor = (
        db.query(GitHubIdentity)
        .filter_by(user_id=ctx.get("uid"))
        .first()
    )

    if not (
        _github_identity_complete(actor)
        and actor.github_user_id == conn.owner_github_account_id
    ):
        owner = f"@{conn.owner_login}" if conn.owner_login else "the repository owner"
        raise HTTPException(403, f"Waiting for repository owner {owner}")


def _github_app_authorization_url() -> str:
    settings = get_settings()
    if not settings.github_app_slug:
        raise HTTPException(503, "ETIS GitHub App authorization is not configured")
    return f"https://github.com/apps/{settings.github_app_slug}/installations/new"


def _repository_authorization_context(
    team_id: int,
    request: Request,
    db: Session,
) -> tuple[dict, Team, RepositoryConnection, str]:
    ctx = require_authenticated(request)
    team = require_team_access(db, ctx, team_id)
    require_team_mutable(db, team.id)
    _require_team_configuration_actor(db, ctx, team)

    conn = db.query(RepositoryConnection).filter_by(team_id=team.id).first()
    if not conn:
        raise HTTPException(404, "No repository candidate exists for this team")
    if conn.status != REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED:
        raise HTTPException(409, "Repository owner authorization is not currently required")
    if conn.owner_type not in {REPOSITORY_OWNER_USER, REPOSITORY_OWNER_ORGANIZATION}:
        raise HTTPException(409, "Repository owner identity is not ready for authorization")
    if conn.owner_type == REPOSITORY_OWNER_USER:
        _require_personal_repository_owner(db, ctx, conn)

    return ctx, team, conn, _github_app_authorization_url()


def _repository_context(
    conn: RepositoryConnection | None,
    gh: GitHubIdentity | None,
):
    if not conn:
        return None

    owner_is_current_user = None

    if (
        conn.owner_type == REPOSITORY_OWNER_USER
        and conn.owner_github_account_id
    ):
        owner_is_current_user = bool(
            gh
            and gh.github_user_id
            and gh.github_user_id == conn.owner_github_account_id
        )

    authorization_url = None
    organization_request_url = None

    if conn.status == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED:
        if (
            conn.owner_type == REPOSITORY_OWNER_USER
            and owner_is_current_user
        ):
            authorization_url = (
                f"/api/v1/onboarding/teams/{conn.team_id}"
                "/repository/authorize"
            )
        elif conn.owner_type == REPOSITORY_OWNER_ORGANIZATION:
            organization_request_url = (
                f"/api/v1/onboarding/teams/{conn.team_id}"
                "/repository/authorize"
            )

    return {
        "status": conn.status,
        "clone_url": conn.clone_url,
        "repo_full_name": conn.repo_full_name,
        "app_installed": conn.github_app_installed,
        "owner_type": conn.owner_type,
        "owner_login": conn.owner_login,
        "owner_is_current_user": owner_is_current_user,
        "authorization_url": authorization_url,
        "organization_request_url": organization_request_url,
        "authorization_started": bool(conn.authorization_requested_at),
        "authorization_requested_at": (
            conn.authorization_requested_at.isoformat()
            if conn.authorization_requested_at
            else None
        ),
        "production_test_repository": is_comp330_starter_kit(
            conn.repo_full_name
        ),
        "organization_approval_required": bool(
            conn.status
            == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
            and conn.owner_type == REPOSITORY_OWNER_ORGANIZATION
        ),
    }

@router.get("/users/{user_id}")
def user_context(user_id:int,request:Request,db:Session=Depends(get_db)):
    ctx = require_authenticated(request)
    caller_user_id = ctx.get("uid")

    # Users may always view their own current onboarding context. Access to
    # another user's current onboarding information must come from
    # lifecycle-valid, database-backed teaching-staff authority.
    if ctx.get("role") != "developer" and caller_user_id != user_id:
        section_ids = accessible_section_ids(db, ctx)

        if section_ids is None:
            pass
        elif not section_ids:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this user's onboarding context",
            )
        else:
            target_section_ids = active_student_section_ids(db, user_id)

            if not target_section_ids.intersection(section_ids):
                raise HTTPException(
                    status_code=403,
                    detail="You are not authorized to view this user's onboarding context",
                )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    ident=db.query(InstitutionalIdentity).filter_by(user_id=user_id).first(); gh=db.query(GitHubIdentity).filter_by(user_id=user_id).first()
    enrollments=active_student_enrollments(db,user_id)
    sections=[]
    for enr in enrollments:
        sec=db.get(CourseSection,enr.section_id)
        tm=(db.query(TeamMembership,Team).join(Team,TeamMembership.team_id==Team.id).join(TeamSection,TeamSection.team_id==Team.id).filter(TeamSection.section_id==sec.id,TeamMembership.user_id==user_id).first())
        team=tm.Team if tm else None
        conn=db.query(RepositoryConnection).filter_by(team_id=team.id).first() if team else None
        members=[]
        if team:
            for membership in db.query(TeamMembership).filter_by(team_id=team.id).all():
                member=db.get(User,membership.user_id); member_gh=db.query(GitHubIdentity).filter_by(user_id=membership.user_id).first()
                if member:
                    members.append({
                        "user_id":member.id,
                        "name":member.display_name,
                        "responsibility_role":membership.responsibility_role,
                        "github_login":(
                            member_gh.github_login
                            if _github_identity_complete(member_gh)
                            else None
                        ),
                        "repository_owner":bool(
                            conn
                            and member_gh
                            and conn.owner_github_account_id
                            and member_gh.github_user_id
                            == conn.owner_github_account_id
                        ),
                    })
        sections.append({"section":{"id":sec.id,"section_key":sec.section_key,"display_name":sec.display_name},"phase_access":phase_access(db,sec.id),"team":{"id":team.id,"team_key":team.team_key,"name":team.name,"project_name":team.project_name,"repo_full_name":team.repo_full_name,"members":members} if team else None,"repository":_repository_context(conn,gh)})
    github_identity_complete = _github_identity_complete(gh)
    return {
        "user":{
            "id":user.id,
            "name":user.display_name,
            "role":user.role,
            "student_id":ident.student_id if ident else None,
            "email":ident.institutional_email if ident else None,
            "github_login":gh.github_login if github_identity_complete else None,
        },
        "sections":sections,
        "onboarding":{
            "institutional_identity":bool(ident),
            "github_identity":github_identity_complete,
            "github_identity_relink_required":bool(gh and not github_identity_complete),
            "team_assigned":any(x["team"] for x in sections),
            "repository_connected":any(
                x["repository"]
                and x["repository"]["status"] in {"verified","connected"}
                for x in sections
            ),
        },
    }

@router.post("/teams/{team_id}/repository")
def connect_repository(team_id:int,req:ConnectRepository,request:Request,db:Session=Depends(get_db)):
    ctx=require_authenticated(request)

    # Team access is determined from current database state. A stale staff role
    # embedded in an unexpired session must not grant repository-binding access.
    authorized_team = require_team_access(db, ctx, team_id)
    require_team_mutable(db, authorized_team.id)

    _require_team_configuration_actor(db, ctx, authorized_team)

    actor_user_id = ctx.get("uid")

    if ctx.get("role") == "developer":
        # Local development may explicitly attribute seeded actions.
        actor_user_id = req.user_id
    else:
        actor_membership = db.query(TeamMembership).filter_by(
            team_id=authorized_team.id,
            user_id=actor_user_id,
        ).first()
        if actor_membership:
            actor_github = db.query(GitHubIdentity).filter_by(
                user_id=actor_user_id,
            ).first()
            if not _github_identity_complete(actor_github):
                raise HTTPException(
                    409,
                    "Reconnect your GitHub identity before connecting the team repository",
                )

    # Lock the team row while binding the one authoritative repository so two
    # teammates onboarding at the same moment cannot create competing bindings.
    team=(
        db.query(Team)
        .filter_by(id=team_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not team:
        raise HTTPException(404,"Team not found")

    # Membership/staff/lifecycle authority may have changed while waiting for
    # the team lock. Re-resolve it before changing candidate state.
    ctx=require_authenticated(request)
    team=require_team_access(db,ctx,team.id)
    require_team_mutable(db,team.id)
    _require_team_configuration_actor(db,ctx,team)
    actor_user_id=ctx.get("uid") if ctx.get("role") != "developer" else req.user_id

    if ctx.get("role") != "developer":
        actor_membership=db.query(TeamMembership).filter_by(
            team_id=team.id,user_id=actor_user_id
        ).first()
        if actor_membership:
            actor_github=db.query(GitHubIdentity).filter_by(
                user_id=actor_user_id
            ).first()
            if not _github_identity_complete(actor_github):
                raise HTTPException(
                    409,
                    "Reconnect your GitHub identity before connecting the team repository",
                )

    try: full_name,clone=repo_name_from_clone(req.clone_url)
    except ValueError as e: raise HTTPException(400,str(e)) from e
    existing=db.query(RepositoryConnection).filter_by(team_id=team_id).first()

    # Once a team repository is verified, students may not replace it.
    # Re-nominating the exact same verified repository is harmless and leaves
    # authoritative state unchanged.
    if existing and existing.status in {REPOSITORY_STATUS_VERIFIED, "connected"}:
        if existing.repo_full_name != full_name:
            raise HTTPException(
                409,
                "This team already has an authoritative repository. "
                "An instructor must replace it.",
            )
        return {
            "repo_full_name": existing.repo_full_name,
            "clone_url": existing.clone_url,
            "status": REPOSITORY_STATUS_VERIFIED,
            "verified": True,
            "suggested_project_name": team.project_name,
            "github_app_install_url": None,
            "message": "This repository is already the verified team repository.",
        }

    starter_kit=is_comp330_starter_kit(full_name)

    if starter_kit:
        ident=(
            db.query(InstitutionalIdentity)
            .filter_by(user_id=actor_user_id)
            .first()
            if actor_user_id is not None
            else None
        )

        settings=get_settings()

        production_test_starter_kit=(
            is_configured_production_test_email(
                ident.institutional_email if ident else None,
                settings.etis_production_test_student_email,
            )
        )

        if not production_test_starter_kit:
            raise HTTPException(
                409,
                "This is the shared COMP 330 starter kit, not your team's "
                "working repository. Paste the HTTPS URL for your team's "
                "own repository.",
            )

        # Deliberately narrow production-acceptance fixture:
        #
        # - exact configured test email only;
        # - this exact public repository only;
        # - ordinary team/course authorization above still applies;
        # - no arbitrary repository, Gmail-domain, PAT, OAuth-token, or
        #   organization-authority bypass is introduced.
        try:
            GitHubEvidenceProvider().head_sha(
                COMP330_STARTER_KIT_REPOSITORY
            )
        except Exception as exc:
            raise HTTPException(
                502,
                (
                    "Production test starter repository is not readable: "
                    f"{exc}"
                ),
            ) from exc

        suggested_project=(
            full_name.split("/",1)[-1]
            .replace("-"," ")
            .title()
        )

        if not existing:
            existing=RepositoryConnection(
                team_id=team_id,
                repo_full_name=full_name,
                clone_url=clone,
                status=REPOSITORY_STATUS_VERIFIED,
                connected_by_user_id=actor_user_id,
                github_app_installed=False,
            )
            db.add(existing)
        else:
            existing.repo_full_name=full_name
            existing.clone_url=clone
            existing.status=REPOSITORY_STATUS_VERIFIED
            existing.connected_by_user_id=actor_user_id
            existing.owner_github_account_id=None
            existing.github_app_installed=False
            existing.installation_id=""
            existing.authorization_requested_at=None

        existing.owner_type=REPOSITORY_OWNER_ORGANIZATION
        existing.owner_login=full_name.split("/",1)[0]
        existing.verified_at=datetime.now(timezone.utc)

        team.repo_full_name=full_name

        if not team.project_name or team.project_name in {
            "Project not confirmed",
            "CampusConnect",
        }:
            team.project_name=suggested_project

        db.commit()

        return {
            "repo_full_name":full_name,
            "clone_url":clone,
            "status":REPOSITORY_STATUS_VERIFIED,
            "verified":True,
            "production_test_repository":True,
            "suggested_project_name":suggested_project,
            "github_app_install_url":None,
            "message":"Production acceptance test repository connected.",
        }

    # Nomination is intentionally not verification. A nominated repository is
    # only a candidate until ownership and GitHub App authorization are proven.
    # Candidate state must never populate Team.repo_full_name, which is the
    # authoritative evidence source used by reviews.
    status=REPOSITORY_STATUS_CANDIDATE
    verified=False

    if not existing:
        existing=RepositoryConnection(
            team_id=team_id,
            repo_full_name=full_name,
            clone_url=clone,
            status=status,
            connected_by_user_id=actor_user_id,
            github_app_installed=False,
        )
        db.add(existing)
    else:
        # Unverified candidates remain mutable. Changing the candidate clears
        # any ownership/authorization observations associated with the old one.
        existing.repo_full_name=full_name
        existing.clone_url=clone
        existing.status=status
        existing.connected_by_user_id=actor_user_id
        existing.owner_type=None
        existing.owner_login=None
        existing.owner_github_account_id=None
        existing.github_app_installed=False
        existing.installation_id=""
        existing.authorization_requested_at=None
        existing.verified_at=None

    # Fail closed: candidates are never authoritative evidence repositories.
    team.repo_full_name=""

    # Resolve only the account that owns the repository namespace. This does
    # not verify repository access and does not authorize the GitHub App.
    owner_resolution_error=None
    actor_is_owner=None

    try:
        owner=repository_owner_identity(full_name)

        existing.owner_type=owner.owner_type
        existing.owner_login=owner.login
        existing.owner_github_account_id=owner.account_id
        existing.status=REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        status=REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED

        # Personal repository ownership is determined using GitHub's immutable
        # account ID rather than a display/login string. Organization approval
        # authority is deliberately not inferred here.
        if owner.owner_type == REPOSITORY_OWNER_USER:
            actor_github=(
                db.query(GitHubIdentity)
                .filter_by(user_id=actor_user_id)
                .first()
                if actor_user_id is not None
                else None
            )

            actor_is_owner=bool(
                actor_github
                and actor_github.github_user_id
                and actor_github.github_user_id == owner.account_id
            )

    except GitHubOwnerResolutionError:
        # Preserve the candidate rather than silently clearing it when GitHub
        # account metadata cannot be resolved. No authorization action is
        # exposed until ownership is known.
        owner_resolution_error=(
            "GitHub could not confirm the repository owner yet. "
            "The candidate was saved and can be retried or changed."
        )

    suggested_project=full_name.split("/",1)[-1].replace("-"," ").title()

    # Candidate nomination is not authoritative project configuration. Return
    # the suggestion to the UI, but do not mutate Team.project_name until a
    # separate explicit project confirmation (or a verified fixture path).
    db.commit()

    return {
        "repo_full_name": full_name,
        "clone_url": clone,
        "status": status,
        "verified": verified,
        "suggested_project_name": suggested_project,
        "github_app_install_url": None,
        "owner_type": existing.owner_type,
        "owner_login": existing.owner_login,
        "owner_github_account_id": existing.owner_github_account_id,
        "actor_is_owner": actor_is_owner,
        "owner_resolution_error": owner_resolution_error,
        "message": (
            "Repository owner identified; owner authorization is required."
            if status == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
            else (
                "Repository candidate recorded. GitHub owner identity must be "
                "resolved before authorization can continue."
            )
        ),
    }

@router.put("/teams/{team_id}/project")
def confirm_project(team_id:int,req:ConfirmProject,request:Request,db:Session=Depends(get_db)):
    ctx = require_authenticated(request)

    # Project metadata is authoritative team configuration. Resolve permission
    # from current database relationships rather than a role embedded in an
    # already-issued session token.
    team = require_team_access(db, ctx, team_id)
    require_team_mutable(db, team.id)
    _require_team_configuration_actor(db, ctx, team)

    team=(
        db.query(Team)
        .filter_by(id=team.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not team:
        raise HTTPException(404,"Team not found")

    ctx=require_authenticated(request)
    team=require_team_access(db,ctx,team.id)
    require_team_mutable(db,team.id)
    _require_team_configuration_actor(db,ctx,team)

    team.project_name = req.project_name.strip()
    if req.team_name:
        team.name = req.team_name.strip()

    db.commit()
    return {
        "team_id": team.id,
        "team_name": team.name,
        "project_name": team.project_name,
    }

@router.get("/teams/{team_id}/repository/authorize")
def authorize_repository(
    team_id:int,
    request:Request,
    db:Session=Depends(get_db),
):
    """Side-effect-free compatibility navigation to GitHub App authorization."""
    _ctx, _team, _conn, authorization_url = _repository_authorization_context(
        team_id, request, db
    )
    return RedirectResponse(authorization_url, status_code=303)


@router.post("/teams/{team_id}/repository/authorize")
def begin_repository_authorization(
    team_id:int,
    request:Request,
    db:Session=Depends(get_db),
):
    """Record an explicit authorization attempt and return GitHub navigation."""
    _ctx, team, _conn, _authorization_url = _repository_authorization_context(
        team_id, request, db
    )

    # Serialize this explicit state transition with candidate/reset changes.
    locked_team=(
        db.query(Team)
        .filter_by(id=team.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not locked_team:
        raise HTTPException(404,"Team not found")

    db.expire_all()
    _ctx, _team, conn, authorization_url = _repository_authorization_context(
        team_id, request, db
    )
    conn=(
        db.query(RepositoryConnection)
        .filter_by(id=conn.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not conn:
        raise HTTPException(404,"No repository candidate exists for this team")

    # Revalidate after the connection lock as well; owner identity or state may
    # have changed while another transaction completed.
    if conn.status != REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED:
        raise HTTPException(409,"Repository owner authorization is not currently required")
    if conn.owner_type == REPOSITORY_OWNER_USER:
        _require_personal_repository_owner(db,_ctx,conn)

    conn.authorization_requested_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "authorization_url": authorization_url,
        "authorization_requested_at": conn.authorization_requested_at.isoformat(),
    }


@router.post("/teams/{team_id}/repository/reset")
def reset_repository_onboarding(
    team_id:int,
    request:Request,
    db:Session=Depends(get_db),
):
    """Bounded staff recovery from a verified or stale repository binding.

    Frozen evidence/review snapshots are historical records and are deliberately
    untouched. Only current/future repository onboarding state is reset.
    """
    ctx = require_authenticated(request)
    team = require_team_access(db, ctx, team_id)
    require_team_mutable(db, team.id)
    _require_repository_recovery_actor(db, ctx, team)

    locked_team = (
        db.query(Team)
        .filter_by(id=team.id)
        .with_for_update()
        .first()
    )
    if not locked_team:
        raise HTTPException(404, "Team not found")

    conn = (
        db.query(RepositoryConnection)
        .filter_by(team_id=team.id)
        .with_for_update()
        .first()
    )

    # Staff/lifecycle authority may have changed while waiting for either lock.
    ctx=require_authenticated(request)
    locked_team=require_team_access(db,ctx,locked_team.id)
    require_team_mutable(db,locked_team.id)
    _require_repository_recovery_actor(db,ctx,locked_team)

    locked_team.repo_full_name = ""
    if conn:
        db.delete(conn)
    db.commit()

    return {
        "team_id": locked_team.id,
        "status": "no_repository",
        "repo_full_name": "",
        "message": (
            "Repository onboarding reset. Historical evidence and reviews were preserved."
        ),
    }


@router.post("/teams/{team_id}/repository/verify")
def verify_repository(team_id:int,request:Request,db:Session=Depends(get_db)):
    ctx = require_authenticated(request)

    # Repository verification promotes candidate state into authoritative team
    # evidence configuration. Team read access alone is insufficient.
    team = require_team_access(db, ctx, team_id)
    require_team_mutable(db, team.id)
    _require_team_configuration_actor(db, ctx, team)

    actor_user_id = ctx.get("uid")
    actor_membership = (
        db.query(TeamMembership)
        .filter_by(team_id=team.id, user_id=actor_user_id)
        .first()
        if actor_user_id is not None
        else None
    )
    if ctx.get("role") != "developer" and actor_membership:
        actor_github = db.query(GitHubIdentity).filter_by(
            user_id=actor_user_id
        ).first()
        if not _github_identity_complete(actor_github):
            raise HTTPException(
                409,
                "Reconnect your GitHub identity before verifying the team repository",
            )

    conn = db.query(RepositoryConnection).filter_by(team_id=team.id).first()
    if not conn:
        raise HTTPException(404, "No repository has been identified for this team")

    if (
        conn.status == REPOSITORY_STATUS_VERIFIED
        and team.repo_full_name == conn.repo_full_name
    ):
        return {
            "verified": True,
            "repo_full_name": conn.repo_full_name,
            "status": conn.status,
        }

    if conn.status != REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED:
        raise HTTPException(
            409,
            "Repository owner authorization must be resolved before verification",
        )

    if conn.owner_type not in {REPOSITORY_OWNER_USER, REPOSITORY_OWNER_ORGANIZATION}:
        raise HTTPException(
            409,
            "Repository owner identity must be resolved before verification",
        )

    if conn.owner_type == REPOSITORY_OWNER_USER:
        _require_personal_repository_owner(db, ctx, conn)

    # Capture exactly what is being externally verified. We deliberately do not
    # hold a database lock while waiting on GitHub. Instead we re-lock/re-read
    # authoritative state afterward and refuse promotion if the candidate moved.
    candidate = (
        conn.id,
        conn.repo_full_name,
        conn.status,
        conn.owner_type,
        conn.owner_login,
        conn.owner_github_account_id,
    )
    candidate_repo = conn.repo_full_name

    try:
        GitHubEvidenceProvider().head_sha(candidate_repo)
    except Exception as e:
        raise HTTPException(
            502,
            detail=f"Repository access is not ready: {e}",
        ) from e

    # The external check may have taken long enough for another teammate or
    # replica to change the candidate. Expire the identity map, lock the Team
    # and RepositoryConnection rows, and compare against the exact candidate
    # that GitHub just proved before promoting anything.
    db.expire_all()

    locked_team = (
        db.query(Team)
        .filter_by(id=team_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not locked_team:
        raise HTTPException(404, "Team not found")

    # Authorization/lifecycle state can change while GitHub is being checked.
    ctx = require_authenticated(request)
    require_team_access(db, ctx, locked_team.id)
    require_team_mutable(db, locked_team.id)
    _require_team_configuration_actor(db, ctx, locked_team)

    locked_conn = (
        db.query(RepositoryConnection)
        .filter_by(team_id=locked_team.id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    actual = (
        locked_conn.id,
        locked_conn.repo_full_name,
        locked_conn.status,
        locked_conn.owner_type,
        locked_conn.owner_login,
        locked_conn.owner_github_account_id,
    ) if locked_conn else None

    if actual != candidate:
        raise HTTPException(
            409,
            "Repository candidate changed while verification was in progress; verify the current candidate again",
        )

    if locked_conn.owner_type == REPOSITORY_OWNER_USER:
        _require_personal_repository_owner(db, ctx, locked_conn)

    locked_conn.status = REPOSITORY_STATUS_VERIFIED
    locked_conn.github_app_installed = bool(get_settings().github_app_id)
    locked_conn.verified_at = datetime.now(timezone.utc)
    locked_team.repo_full_name = locked_conn.repo_full_name

    db.commit()

    return {
        "verified": True,
        "repo_full_name": locked_conn.repo_full_name,
        "status": locked_conn.status,
    }
