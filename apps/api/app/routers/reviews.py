import hashlib
import json
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import EvidenceSnapshot, ReviewSession, ReviewTurn, Team, User, TeamSection, TeamMembership, ReviewFindingState
from ..schemas import ReviewStartRequest, ReviewResponseRequest, ReviewClarifyRequest, ReviewCoachRequest, EvidenceDisputeRequest, FindingDispositionRequest
from ..services.challenge_engine import ChallengeEngine, Challenge, reviewer_profile, default_memory
from ..services.review_orchestrator import ReviewOrchestrator
from ..services.review_planning import build_review_objective, initialize_review_control
from ..services.evidence import snapshot_from_dict
from ..services.evidence_package import EvidencePackageBuilder
from ..services.usage_store import record_usage_events
from ..services.course_admin import phase_access
from ..services.auth import (
    STAFF_ROLES,
    accessible_section_ids,
    auth_context,
    require_authenticated,
    require_section_role,
    require_team_access,
)
from ..services.semester_lifecycle import active_student_section_ids, require_team_mutable

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"], dependencies=[Depends(require_authenticated)])


def _finding_states(db: Session, snapshot_id: int) -> dict[str, dict]:
    rows=db.query(ReviewFindingState).filter_by(snapshot_id=snapshot_id).all()
    return {r.finding_id:{"status":r.status,"evidence_path":r.evidence_path,"rationale":r.rationale,"updated_at":r.updated_at.isoformat() if r.updated_at else None} for r in rows}


def _upsert_finding_state(db: Session, *, team_id:int, snapshot_id:int, finding_id:str, status:str, user_id:int|None, evidence_path:str='', rationale:str=''):
    row=db.query(ReviewFindingState).filter_by(snapshot_id=snapshot_id,finding_id=finding_id).first()
    if not row:
        row=ReviewFindingState(team_id=team_id,snapshot_id=snapshot_id,finding_id=finding_id)
        db.add(row)
    row.status=status; row.evidence_path=evidence_path or row.evidence_path; row.rationale=rationale or row.rationale; row.created_by_user_id=user_id or row.created_by_user_id
    return row


def _decorate_finding_states(evidence:dict, states:dict[str,dict]):
    for key in ('findings','challenge_candidates'):
        for finding in evidence.get(key,[]):
            finding['lifecycle']=states.get(finding.get('id'),{"status":"open"})
    return evidence
engine = ChallengeEngine()
orchestrator = ReviewOrchestrator(challenge_engine=engine)
evidence_package_builder = EvidencePackageBuilder()
_session_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


def _session_lock(session_id: int):
    with _locks_guard:
        return _session_locks.setdefault(session_id, threading.Lock())


def _review_session_for_update_stmt(session_id: int):
    """
    Build the authoritative database row-lock statement for review mutation.

    PostgreSQL SELECT ... FOR UPDATE serializes mutations to the same review
    session across independent application replicas. populate_existing forces
    SQLAlchemy to refresh an already-loaded ReviewSession after any lock wait,
    preventing post-lock logic from continuing with stale pre-wait state.
    """
    return (
        select(ReviewSession)
        .where(ReviewSession.id == session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _evidence_snapshot_for_update_stmt(snapshot_id: int):
    """
    Build the authoritative database row-lock statement for finding-state
    mutation shared across review sessions.

    Multiple review sessions may reference the same immutable evidence snapshot.
    Locking the snapshot row serializes updates to snapshot-scoped finding state
    across those independent sessions.
    """
    return (
        select(EvidenceSnapshot)
        .where(EvidenceSnapshot.id == snapshot_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _team_for_update_stmt(team_id: int):
    """
    Build the authoritative database row-lock statement for team-scoped
    review-start and frozen-snapshot establishment.

    PostgreSQL SELECT ... FOR UPDATE ensures that only one application replica
    at a time can decide whether a team's frozen evidence snapshot should be
    reused or created.
    """
    return (
        select(Team)
        .where(Team.id == team_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _challenge_from_state(state: dict) -> Challenge:
    raw = dict(state["challenge"])
    raw.pop("reviewer", None)
    raw.pop("coaching_mode", None)
    return Challenge(**raw)


def _safe_json(value, default):
    try:
        return json.loads(value or "")
    except Exception:
        return default


def _idempotency_fingerprint(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _legacy_idempotency_payload(
    student_turn: ReviewTurn,
    signals: dict,
    operation: str,
) -> dict | None:
    """
    Reconstruct request identity for turns created before payload fingerprints
    were persisted.

    Historical coach turns did not retain the requested decision, so they
    cannot always be verified safely. In that case fail closed rather than
    silently treating a potentially different request as a duplicate.
    """
    if operation == "clarify":
        return {
            "question": student_turn.content,
        }

    if operation == "respond":
        return {
            "response": student_turn.content,
            "evidence_refs": _safe_json(
                student_turn.evidence_refs_json,
                [],
            ),
            "decision": signals.get("decision"),
            "intent": signals.get("selected_intent") or "discuss",
        }

    if operation == "coach":
        if "decision" not in signals:
            return None
        return {
            "decision": signals.get("decision"),
        }

    return None


def _idempotent_result(
    db: Session,
    session_id: int,
    client_turn_id: str | None,
    expected_operation: str,
    expected_payload: dict | None = None,
):
    if not client_turn_id:
        return None

    student_turn = (
        db.query(ReviewTurn)
        .filter_by(
            session_id=session_id,
            client_turn_id=client_turn_id,
        )
        .first()
    )
    if not student_turn:
        return None

    signals = _safe_json(student_turn.signals_json, {})
    actual_operation = signals.get("idempotency_operation")

    # Compatibility inference is intentionally narrow. client_turn_id became
    # a first-class column in this release, but this also makes the helper
    # robust if a development fixture omits the explicit operation marker.
    if not actual_operation:
        if (
            student_turn.lens == "evidence_dispute"
            or signals.get("kind") == "evidence_dispute"
        ):
            actual_operation = "evidence_dispute"
        elif signals.get("kind") == "student_coach_request":
            actual_operation = "coach"
        elif (
            signals.get("kind") == "student_conversation"
            and signals.get("selected_intent") == "clarify"
        ):
            actual_operation = "clarify"
        else:
            actual_operation = "respond"

    if actual_operation != expected_operation:
        raise HTTPException(
            409,
            "client_turn_id was already used for a different review operation",
        )

    if expected_payload is not None:
        expected_fingerprint = _idempotency_fingerprint(expected_payload)
        original_fingerprint = signals.get("idempotency_fingerprint")

        if not original_fingerprint:
            original_payload = _legacy_idempotency_payload(
                student_turn,
                signals,
                actual_operation,
            )
            if original_payload is None:
                raise HTTPException(
                    409,
                    "client_turn_id retry payload cannot be safely verified",
                )
            original_fingerprint = _idempotency_fingerprint(
                original_payload
            )

        if original_fingerprint != expected_fingerprint:
            raise HTTPException(
                409,
                "client_turn_id was already used for a different request payload",
            )

    reviewer = (
        db.query(ReviewTurn)
        .filter(
            ReviewTurn.session_id == session_id,
            ReviewTurn.sequence > student_turn.sequence,
            ReviewTurn.actor == "reviewer",
        )
        .order_by(ReviewTurn.sequence)
        .first()
    )
    if not reviewer:
        return None

    rs = _safe_json(reviewer.signals_json, {})
    return {
        "duplicate": True,
        "follow_up": {
            "text": reviewer.content,
            "lens": reviewer.lens,
            "reviewer": rs.get("reviewer"),
            "kind": rs.get("kind"),
            "provider": rs.get("provider"),
            "model": rs.get("model"),
            "target_move": rs.get("target_move"),
            "guidance_refs": rs.get("guidance_refs", []),
            "teach_back": rs.get("teach_back", False),
        },
    }


def _add_reviewer_turn(db: Session, session_id: int, sequence: int, payload: dict):
    db.add(
        ReviewTurn(
            session_id=session_id,
            sequence=sequence,
            actor="reviewer",
            lens=payload.get("lens", "chief_architect"),
            content=payload.get("text", ""),
            evidence_refs_json=json.dumps(payload.get("evidence_refs", [])),
            signals_json=json.dumps(
                {
                    "provider": payload.get("provider", "deterministic"),
                    "kind": payload.get("kind", "coaching"),
                    "reviewer": payload.get("reviewer", reviewer_profile(payload.get("lens", "chief_architect"))),
                    "coaching_level": payload.get("coaching_level"),
                    "ready_to_commit": payload.get("ready_to_commit", False),
                    "target_move": payload.get("target_move"),
                    "interpreted_intent": payload.get("interpreted_intent"),
                    "guidance_refs": payload.get("guidance_refs", []),
                    "understood_points": payload.get("understood_points", []),
                    "teach_back": payload.get("teach_back", False),
                    "model": payload.get("model"),
                }
            ),
        )
    )


def _history_payload(turns):
    return [
        {
            "sequence": turn.sequence,
            "actor": turn.actor,
            "lens": turn.lens,
            "content": turn.content,
            "signals": _safe_json(turn.signals_json, {}),
        }
        for turn in turns[-14:]
    ]


def _student_for_session(db: Session, session: ReviewSession):
    return db.get(User, session.user_id)


def _evidence_context(db: Session, state: dict):
    compact = state.get("compact_evidence_package")
    if compact:
        return json.dumps(compact, ensure_ascii=False)
    snapshot_id = state.get("evidence_snapshot_id")
    if not snapshot_id:
        return ""
    snapshot = db.get(EvidenceSnapshot, snapshot_id)
    return snapshot.summary_json if snapshot else ""


def _record_reply_usage(db: Session, reply: dict, session: ReviewSession):
    record_usage_events(
        db, reply.get("usage_events") or [], team_id=session.team_id, user_id=session.user_id,
        session_id=session.id, phase_id=session.phase_id, metadata={"source": "review_turn"}
    )


def _save_memory(state: dict, reply: dict):
    memory = reply.get("conversation_memory")
    if memory:
        state["conversation_memory"] = memory
    state["active_reviewer"] = reply.get("reviewer")
    state["coaching_target"] = reply.get("target_move")




def _authorize_session_read(
    db: Session,
    session: ReviewSession,
    ctx: dict,
):
    if ctx.get("role") == "developer":
        return

    # A student may read their own Review Room only while that team's term
    # still grants current student access. Archived-term history is retained
    # for authorized teaching-staff inspection but is no longer student-visible.
    if session.user_id == ctx.get("uid"):
        require_team_access(db, ctx, session.team_id)
        return

    # Authorized teaching staff may inspect persisted review history, but this
    # helper grants read authority only. Mutation endpoints must use a stricter
    # student or explicitly role-bounded mutation helper below.
    section_link = (
        db.query(TeamSection)
        .filter_by(team_id=session.team_id)
        .first()
    )
    if not section_link:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this review conversation",
        )

    try:
        require_section_role(
            db,
            ctx,
            section_link.section_id,
            STAFF_ROLES,
        )
    except HTTPException as exc:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this review conversation",
        ) from exc


def _authorize_session_student_mutation(
    db: Session,
    session: ReviewSession,
    ctx: dict,
) -> int | None:
    """Authorize a student-originated Review Room mutation.

    Teaching-staff read access never implies authority to speak, decide,
    complete, coach, or dispute evidence as the student. The local developer
    identity remains available only for deterministic development fixtures.
    """
    if ctx.get("role") == "developer":
        return None

    user_id = ctx.get("uid")
    if not user_id or session.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the student who owns this review may perform that action",
        )

    # Re-resolve active semester/team authority from current database state.
    require_team_access(db, ctx, session.team_id)
    require_team_mutable(db, session.team_id)
    membership = db.query(TeamMembership).filter_by(
        team_id=session.team_id,
        user_id=user_id,
    ).first()
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="Only the student who owns this review may perform that action",
        )

    return user_id


FINDING_VALIDATION_STAFF_ROLES = {"course_owner", "instructor"}


def _authorize_finding_disposition_mutation(
    db: Session,
    session: ReviewSession,
    ctx: dict,
    status: str,
) -> int | None:
    if status not in {"confirmed", "corrected", "resolved"}:
        return _authorize_session_student_mutation(db, session, ctx)

    if ctx.get("role") == "developer":
        return None

    require_team_mutable(db, session.team_id)
    section_link = db.query(TeamSection).filter_by(
        team_id=session.team_id
    ).first()
    if not section_link:
        raise HTTPException(
            status_code=403,
            detail="This finding state requires current Instructor or Course Owner validation",
        )

    require_section_role(
        db,
        ctx,
        section_link.section_id,
        FINDING_VALIDATION_STAFF_ROLES,
    )
    return ctx.get("uid")
@router.get("")
def list_reviews(request:Request, team_id: int | None = None, user_id: int | None = None, limit: int = 12, db: Session = Depends(get_db)):
    ctx = auth_context(request)
    caller_user_id = ctx.get("uid")

    query = db.query(ReviewSession)

    if ctx.get("role") == "developer":
        # Local developer access is intentionally unrestricted.
        pass
    else:
        section_ids = accessible_section_ids(db, ctx)

        # An explicit request for another user's review history requires
        # current database-backed teaching-staff authority.
        if (
            user_id is not None
            and user_id != caller_user_id
            and section_ids == set()
        ):
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this student's reviews",
            )

        if section_ids is None:
            # Active course-owner authority is global.
            pass
        elif section_ids:
            # Current teaching staff may only enumerate reviews for teams in
            # sections to which they are actively assigned.
            authorized_team_ids = (
                db.query(TeamSection.team_id)
                .filter(TeamSection.section_id.in_(section_ids))
            )
            query = query.filter(
                ReviewSession.team_id.in_(authorized_team_ids)
            )
        else:
            # No current teaching-staff authority: self-service only. Restrict
            # enumeration to teams in the caller's currently active student
            # sections so retained archived-term review history is not exposed
            # merely because the user has another active Studio enrollment.
            user_id = caller_user_id
            active_section_ids = active_student_section_ids(db, caller_user_id)
            if not active_section_ids:
                query = query.filter(ReviewSession.id == -1)
            else:
                active_team_ids = (
                    db.query(TeamSection.team_id)
                    .filter(TeamSection.section_id.in_(active_section_ids))
                )
                query = query.filter(
                    ReviewSession.team_id.in_(active_team_ids)
                )

    if team_id:
        # Explicit team selection must independently satisfy the current
        # database-backed team authorization contract.
        require_team_access(db, ctx, team_id)
        query = query.filter_by(team_id=team_id)

    if user_id:
        query = query.filter_by(user_id=user_id)

    sessions = (
        query
        .order_by(ReviewSession.started_at.desc())
        .limit(min(max(limit, 1), 50))
        .all()
    )

    return {
        "sessions": [
            {
                "id": session.id,
                "team_id": session.team_id,
                "user_id": session.user_id,
                "phase_id": session.phase_id,
                "status": session.status,
                "mode": session.mode,
                "started_at": session.started_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "evaluation": _safe_json(session.challenge_state_json, {}).get("evaluation"),
                "committed": bool(_safe_json(session.challenge_state_json, {}).get("committed_position")),
            }
            for session in sessions
        ]
    }


def _longitudinal_summary(previous: dict | None, current: dict) -> dict:
    if not previous:
        return {"has_prior_snapshot": False, "message": "This is the first frozen evidence snapshot available for the team."}
    prev_items = {x.get("title"): x.get("status") for x in previous.get("items", [])}
    cur_items = {x.get("title"): x.get("status") for x in current.get("items", [])}
    improved = [k for k, v in cur_items.items() if prev_items.get(k) and prev_items.get(k) != "present" and v == "present"]
    regressed = [k for k, v in cur_items.items() if prev_items.get(k) == "present" and v != "present"]
    return {
        "has_prior_snapshot": True,
        "previous_phase": previous.get("phase_id"),
        "previous_commit_sha": previous.get("commit_sha"),
        "coverage_change": int(current.get("coverage", 0)) - int(previous.get("coverage", 0)),
        "improved_evidence": improved[:12],
        "regressed_evidence": regressed[:12],
        "message": "The current review can compare this phase with the team's previously frozen engineering evidence.",
    }


def _prior_finding_categories(db: Session, team_id: int, phase_id: str, limit: int = 8) -> list[str]:
    sessions = (
        db.query(ReviewSession)
        .filter_by(team_id=team_id, phase_id=phase_id)
        .order_by(ReviewSession.started_at.desc())
        .limit(limit)
        .all()
    )
    out: list[str] = []
    for session in sessions:
        state = _safe_json(session.challenge_state_json, {})
        category = ((state.get("challenge") or {}).get("finding") or {}).get("category")
        if category:
            out.append(category)
    return out


def _prior_student_review_context(db: Session, user_id: int, team_id: int, phase_id: str, limit: int = 3) -> list[dict]:
    rows = (
        db.query(ReviewSession)
        .filter_by(user_id=user_id, team_id=team_id)
        .order_by(ReviewSession.started_at.desc())
        .limit(limit)
        .all()
    )
    out=[]
    for row in rows:
        state=_safe_json(row.challenge_state_json,{})
        out.append({
            "session_id": row.id,
            "phase_id": row.phase_id,
            "mode": row.mode,
            "status": row.status,
            "challenge_title": (state.get("challenge") or {}).get("title"),
            "reasoning_demonstrated": [k for k,v in (state.get("reasoning_state") or {}).items() if v],
            "recommendation": state.get("committed_position"),
        })
    return out


def _review_start_idempotency_payload(
    req: ReviewStartRequest,
    *,
    user_id: int,
    repo_full_name: str,
) -> dict:
    """
    Return the effective Start Review request protected by client_request_id.

    Identity and repository values are the authoritative values resolved by the
    server, not untrusted caller substitutions.
    """
    return {
        "user_id": user_id,
        "phase_id": req.phase_id,
        "mode": req.mode,
        "scenario_id": req.scenario_id or None,
        "repo_full_name": repo_full_name or None,
        "focus": req.focus or None,
        "finding_id": req.finding_id or None,
        "finding_ids": list(req.finding_ids or []),
        "entry_intent": req.entry_intent,
        "source_view": req.source_view,
    }


def _review_start_response(
    db: Session,
    session: ReviewSession,
    *,
    duplicate: bool,
) -> dict:
    """
    Reconstruct the Start Review response entirely from committed state.

    This lets a network retry return the original ReviewSession without
    repeating repository analysis, reviewer preparation, or opening-turn
    creation.
    """
    state = _safe_json(session.challenge_state_json, {})

    team = db.get(Team, session.team_id)
    user = db.get(User, session.user_id)
    if not team or not user:
        raise HTTPException(
            409,
            "The original review session can no longer be reconstructed",
        )

    snapshot_id = state.get("evidence_snapshot_id")
    snapshot = db.get(EvidenceSnapshot, snapshot_id) if snapshot_id else None
    if not snapshot:
        raise HTTPException(
            409,
            "The original review session has no frozen evidence snapshot",
        )

    evidence = _safe_json(snapshot.summary_json, {})
    evidence = _decorate_finding_states(
        evidence,
        _finding_states(db, snapshot.id),
    )

    challenge_payload = dict(state.get("challenge") or {})
    opening_turn = (
        db.query(ReviewTurn)
        .filter_by(
            session_id=session.id,
            sequence=1,
            actor="reviewer",
        )
        .first()
    )
    if not challenge_payload or not opening_turn:
        raise HTTPException(
            409,
            "The original review session is incomplete",
        )

    challenge_payload["opening_text"] = opening_turn.content

    return {
        "session_id": session.id,
        "team": {
            "id": team.id,
            "name": team.name,
            "project_name": team.project_name,
            "phase": session.phase_id,
        },
        "user": {
            "id": user.id,
            "name": user.display_name,
            "role": user.role,
        },
        "challenge": challenge_payload,
        "evidence": evidence,
        "evidence_cache_reused": bool(
            state.get("evidence_cache_reused")
        ),
        "duplicate": duplicate,
    }


@router.post("/start")
def start(req: ReviewStartRequest, request:Request, db: Session = Depends(get_db)):
    ctx = auth_context(request)
    team = require_team_access(db, ctx, req.team_id)

    # Frozen-snapshot establishment is team-scoped. Serialize the entire
    # snapshot cache check and evidence-preparation transaction on the Team row
    # so independent application replicas cannot simultaneously decide that
    # the same team/phase/commit needs a new frozen snapshot.
    locked_team = (
        db.execute(_team_for_update_stmt(team.id))
        .scalar_one_or_none()
    )
    if not locked_team:
        raise HTTPException(404, "Team not found")

    team = locked_team

    # Authorization may have changed while waiting for another replica's Team
    # transaction. Re-evaluate current database-backed identity and access
    # before reading repository configuration or preparing evidence.
    ctx = auth_context(request)
    team = require_team_access(db, ctx, team.id)

    # Review Room sessions are student-owned. Teaching staff may inspect the
    # persisted conversation but cannot start a review on a student's behalf.
    # Development fixtures may still name a seeded subject explicitly.
    if ctx.get("role") != "developer":
        caller_user_id = ctx.get("uid")
        if not caller_user_id or (req.user_id is not None and req.user_id != caller_user_id):
            raise HTTPException(
                status_code=403,
                detail="Only the student may start their Review Room session",
            )

        membership = db.query(TeamMembership).filter_by(
            team_id=team.id,
            user_id=caller_user_id,
        ).first()
        if not membership:
            raise HTTPException(
                status_code=403,
                detail="Only a current student team member may start a review",
            )
        req.user_id = caller_user_id

    user = db.get(User, req.user_id) if req.user_id else None
    if not user or not user.is_active:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    subject_membership = (
        db.query(TeamMembership)
        .filter_by(
            team_id=team.id,
            user_id=user.id,
        )
        .first()
    )
    if not subject_membership:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    prior_student_sessions = _prior_student_review_context(db, user.id, team.id, req.phase_id)
    section_link = db.query(TeamSection).filter_by(team_id=team.id).first()
    if section_link:
        access = phase_access(db, section_link.section_id)
        allowed = set(access.get("released", []))
        if req.phase_id not in allowed:
            raise HTTPException(423, f"{req.phase_id} is not released for this section yet. Students may review released or earlier phases only.")

    authoritative_repo = (team.repo_full_name or "").strip()
    requested_repo = (req.repo_full_name or "").strip()

    if requested_repo and requested_repo.casefold() != authoritative_repo.casefold():
        raise HTTPException(
            status_code=409,
            detail="Repository does not match the team's configured repository",
        )

    repo_full_name = authoritative_repo

    start_request_payload = _review_start_idempotency_payload(
        req,
        user_id=user.id,
        repo_full_name=repo_full_name,
    )

    # The Team row is still locked here. Therefore a second application
    # replica using the same team-scoped client_request_id cannot race this
    # lookup with creation of another ReviewSession.
    if req.client_request_id:
        existing_session = (
            db.query(ReviewSession)
            .filter_by(
                team_id=team.id,
                client_request_id=req.client_request_id,
            )
            .first()
        )

        if existing_session:
            existing_state = _safe_json(
                existing_session.challenge_state_json,
                {},
            )
            original_request = existing_state.get("start_request")

            if original_request != start_request_payload:
                raise HTTPException(
                    409,
                    "client_request_id was already used for a different review start request",
                )

            _authorize_session_student_mutation(
                db,
                existing_session,
                auth_context(request),
            )

            return _review_start_response(
                db,
                existing_session,
                duplicate=True,
            )

    previous_snapshot = db.query(EvidenceSnapshot).filter_by(team_id=team.id).order_by(EvidenceSnapshot.created_at.desc()).first()
    previous_data = _safe_json(previous_snapshot.summary_json, {}) if previous_snapshot else None
    prior_categories = _prior_finding_categories(db, team.id, req.phase_id)
    try:
        cached_evidence = None
        cache_reused = False
        if repo_full_name and not req.scenario_id:
            head_sha = orchestrator.evidence_provider.head_sha(repo_full_name)
            same = (
                db.query(EvidenceSnapshot)
                .filter_by(team_id=team.id, phase_id=req.phase_id, commit_sha=head_sha)
                .order_by(EvidenceSnapshot.created_at.desc())
                .first()
            )
            if same:
                cached_evidence = snapshot_from_dict(_safe_json(same.summary_json, {}))
                cache_reused = True
        excluded=set()
        source_snapshot = same if 'same' in locals() and same else previous_snapshot
        current_sha = cached_evidence.commit_sha if cached_evidence else (orchestrator.evidence_provider.head_sha(repo_full_name) if repo_full_name else '')
        if source_snapshot and source_snapshot.commit_sha == current_sha and source_snapshot.phase_id == req.phase_id:
            excluded={fid for fid,st in _finding_states(db,source_snapshot.id).items() if st.get('status') in {'corrected','resolved'}}
        prepared = orchestrator.prepare(
            repo_full_name,
            req.phase_id,
            scenario_id=req.scenario_id,
            prior_categories=prior_categories,
            cached_evidence=cached_evidence,
            focus=req.focus,
            finding_id=req.finding_id,
            finding_ids=req.finding_ids,
            excluded_finding_ids=excluded,
            entry_intent=req.entry_intent,
        )
        evidence = prepared.evidence
        challenge = prepared.challenge
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    evidence.longitudinal = _longitudinal_summary(previous_data, evidence.to_dict())
    # Reuse the exact same frozen snapshot when the repository commit and phase have not changed.
    # This preserves team-level finding corrections/disputes across multiple student sessions and
    # prevents duplicate snapshot rows for identical evidence.
    if bool(locals().get("cache_reused", False)) and 'same' in locals() and same:
        snapshot = same
    else:
        snapshot = EvidenceSnapshot(
            team_id=team.id,
            phase_id=req.phase_id,
            source=evidence.snapshot_kind,
            commit_sha=evidence.commit_sha,
            summary_json=json.dumps(evidence.to_dict()),
        )
        db.add(snapshot)
        db.flush()
        if previous_snapshot and previous_snapshot.commit_sha == snapshot.commit_sha and previous_snapshot.phase_id == snapshot.phase_id:
            for fid,st in _finding_states(db,previous_snapshot.id).items():
                if st.get('status') in {'corrected','resolved','accepted_risk','deferred','evidence_disputed','confirmed'}:
                    _upsert_finding_state(db,team_id=team.id,snapshot_id=snapshot.id,finding_id=fid,status=st.get('status'),user_id=user.id,evidence_path=st.get('evidence_path',''),rationale=st.get('rationale',''))
    # A Finding Review makes the selected finding(s) an explicit review object.
    # This is team-visible lifecycle state; it does not imply that the finding is confirmed.
    if req.mode == 'finding_review':
        selected = list(dict.fromkeys([*(req.finding_ids or []), *([req.finding_id] if req.finding_id else [])]))[:3]
        valid_ids = {str(f.get('id')) for f in evidence.findings if isinstance(f, dict) and f.get('id')}
        for fid in selected:
            if fid in valid_ids:
                current = _finding_states(db, snapshot.id).get(fid, {})
                if current.get('status', 'open') == 'open':
                    _upsert_finding_state(
                        db, team_id=team.id, snapshot_id=snapshot.id, finding_id=fid,
                        status='under_discussion', user_id=user.id,
                        rationale='Selected for a Finding Review session.'
                    )
        db.flush()
    evidence_payload=_decorate_finding_states(evidence.to_dict(),_finding_states(db,snapshot.id))

    opening = engine.opening_message(challenge, user.display_name)
    memory = default_memory(challenge.lens)
    memory["review_mode"] = req.mode
    memory["review_focus"] = req.focus or ""
    memory["entry_intent"] = req.entry_intent
    memory["source_view"] = req.source_view
    memory["selected_finding_ids"] = req.finding_ids or ([req.finding_id] if req.finding_id else [])
    memory["prior_sessions"] = prior_student_sessions
    memory["last_target"] = opening.get("target_move")
    memory["last_question"] = opening.get("text", "")
    memory["asked_targets"][opening.get("target_move", "consequence_visible")] = 1

    compact_package = evidence_package_builder.build(evidence.to_dict(), challenge.to_dict()).to_dict()
    selected_finding_ids = list(dict.fromkeys([
        *(req.finding_ids or []),
        *([req.finding_id] if req.finding_id else []),
    ]))[:3]
    valid_objective_finding_ids = {
        str(finding.get("id"))
        for finding in evidence.findings
        if isinstance(finding, dict) and finding.get("id")
    }
    selected_finding_ids = [
        finding_id
        for finding_id in selected_finding_ids
        if finding_id in valid_objective_finding_ids
    ]
    review_objective = build_review_objective(
        raw_mode=req.mode,
        phase_id=req.phase_id,
        challenge=challenge,
        focus=req.focus,
        related_finding_ids=selected_finding_ids,
        entry_intent=req.entry_intent,
    )
    review_control = initialize_review_control(
        review_objective,
        reasoning_mode=engine.settings.etis_reasoning_validation_mode,
        planning_mode=engine.settings.etis_review_planning_mode,
    )
    state = {
        "challenge": challenge.to_dict(),
        "compact_evidence_package": compact_package,
        "evidence_cache_reused": bool(locals().get("cache_reused", False)),
        "evidence_snapshot_id": snapshot.id,
        "evaluation": None,
        "turn_count": 1,
        "coaching_level": 0,
        "clarification_count": 0,
        "committed_position": None,
        "reasoning_state": {},
        "coaching_target": opening.get("target_move"),
        "conversation_memory": memory,
        "active_reviewer": opening["reviewer"],
        "finding_categories_reviewed": [challenge.finding.get("category")] if challenge.finding else [],
        "review_focus": req.focus,
        "requested_finding_id": req.finding_id,
        "requested_finding_ids": req.finding_ids,
        "entry_intent": req.entry_intent,
        "source_view": req.source_view,
        "start_request": start_request_payload,
        "evidence_disputes": [],
        "review_control": review_control,
    }

    session = ReviewSession(
        team_id=team.id,
        client_request_id=req.client_request_id,
        user_id=user.id,
        phase_id=req.phase_id,
        mode=req.mode,
        scenario_id=req.scenario_id or "",
        challenge_state_json=json.dumps(state),
    )
    db.add(session)
    db.flush()
    if not bool(locals().get("cache_reused", False)):
        record_usage_events(db, evidence.ai_usage_events or [], team_id=team.id, user_id=user.id, session_id=session.id, phase_id=req.phase_id, metadata={"source": "repository_analysis", "commit_sha": evidence.commit_sha})
    _add_reviewer_turn(db, session.id, 1, opening)
    db.commit()
    db.refresh(session)

    return _review_start_response(
        db,
        session,
        duplicate=False,
    )


@router.get("/evidence/current")
def current_evidence(team_id: int, phase_id: str | None, request: Request, db: Session = Depends(get_db)):
    ctx = auth_context(request)

    # Frozen engineering evidence is team-scoped protected data. Authorization
    # is determined from current database state rather than the role embedded
    # in an already-issued session token.
    team = require_team_access(db, ctx, team_id)

    q = db.query(EvidenceSnapshot).filter_by(team_id=team_id)
    if phase_id:
        q = q.filter_by(phase_id=phase_id)
    snapshot = q.order_by(EvidenceSnapshot.created_at.desc()).first()
    if not snapshot:
        return {"available": False, "team": {"id": team.id, "name": team.name, "project_name": team.project_name, "repo_full_name": team.repo_full_name}}
    evidence = _safe_json(snapshot.summary_json, {})
    evidence = _decorate_finding_states(evidence, _finding_states(db, snapshot.id))
    return {
        "available": True,
        "snapshot_id": snapshot.id,
        "created_at": snapshot.created_at.isoformat(),
        "team": {"id": team.id, "name": team.name, "project_name": team.project_name, "repo_full_name": team.repo_full_name},
        "evidence": evidence,
    }


@router.get("/{session_id}")
def get_review(session_id: int, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_read(db, session, auth_context(request))
    turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    state = _safe_json(session.challenge_state_json, {})
    snapshot = db.get(EvidenceSnapshot, state.get("evidence_snapshot_id")) if state.get("evidence_snapshot_id") else None
    evidence = _safe_json(snapshot.summary_json, {}) if snapshot else None
    if snapshot and evidence:
        evidence=_decorate_finding_states(evidence,_finding_states(db,snapshot.id))
    user = _student_for_session(db, session)
    team = db.get(Team, session.team_id)
    return {
        "session": {
            "id": session.id,
            "team_id": session.team_id,
            "phase_id": session.phase_id,
            "status": session.status,
            "mode": session.mode,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "student": {"id": user.id, "name": user.display_name, "role": user.role} if user else None,
        },
        "team": {"id": team.id, "name": team.name, "project_name": team.project_name, "repo_full_name": team.repo_full_name} if team else None,
        "snapshot": {"id": snapshot.id, "commit_sha": snapshot.commit_sha, "source": snapshot.source, "created_at": snapshot.created_at.isoformat()} if snapshot else None,
        "state": state,
        "evidence": evidence,
        "turns": [
            {
                "sequence": turn.sequence,
                "actor": turn.actor,
                "lens": turn.lens,
                "content": turn.content,
                "evidence_refs": _safe_json(turn.evidence_refs_json, []),
                "signals": _safe_json(turn.signals_json, {}),
                "created_at": turn.created_at.isoformat(),
            }
            for turn in turns
        ],
    }


@router.post("/{session_id}/clarify")
def clarify(session_id: int, req: ReviewClarifyRequest, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_student_mutation(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")
    duplicate = _idempotent_result(
            db,
            session_id,
            req.client_turn_id,
            "clarify",
            {"question": req.question},
        )
    if duplicate:
        state = _safe_json(session.challenge_state_json, {})
        reply = duplicate["follow_up"]
        return {
            "duplicate": True,
            "reply": reply,
            "turn_count": state.get("turn_count", 0),
            "clarification_count": state.get("clarification_count", 0),
            "evaluation": state.get("evaluation"),
            "reasoning_state": state.get("reasoning_state", {}),
        }
    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The reviewer is still responding to the previous turn. Please wait for that response.")
    try:
        # Same-process locking is only a fast-fail optimization. The database
        # row lock is the authoritative serializer across application replicas.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session
        _authorize_session_student_mutation(db, session, auth_context(request))
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        # Re-check idempotency while holding the authoritative database lock.
        duplicate = _idempotent_result(
            db,
            session_id,
            req.client_turn_id,
            "clarify",
            {"question": req.question},
        )
        if duplicate:
            state = _safe_json(session.challenge_state_json, {})
            reply = duplicate["follow_up"]
            return {
                "duplicate": True,
                "reply": reply,
                "turn_count": state.get("turn_count", 0),
                "clarification_count": state.get("clarification_count", 0),
                "evaluation": state.get("evaluation"),
                "reasoning_state": state.get("reasoning_state", {}),
            }

        state = _safe_json(session.challenge_state_json, {})
        challenge = _challenge_from_state(state)
        turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
        sequence = (turns[-1].sequence if turns else 0) + 1
        student = _student_for_session(db, session)
        prior = state.get("reasoning_state") or {}
        reply, merged, evaluation = engine.converse(
            challenge, req.question, prior, intent="clarify",
            coaching_level=state.get("coaching_level", 0), evidence_context=_evidence_context(db, state),
            conversation_history=_history_payload(turns), conversation_memory=state.get("conversation_memory") or {},
            student_name=student.display_name if student else "",
        )
        db.add(ReviewTurn(
            session_id=session_id, sequence=sequence, client_turn_id=req.client_turn_id,
            actor="student", lens="conversation", content=req.question,
            evidence_refs_json="[]", signals_json=json.dumps({
                "kind": "student_conversation", "selected_intent": "clarify",
                "idempotency_operation": "clarify",
                "idempotency_fingerprint": _idempotency_fingerprint(
                    {"question": req.question}
                ),
                "interpreted_intent": reply.get("interpreted_intent"), "client_turn_id": req.client_turn_id,
            }),
        ))
        _add_reviewer_turn(db, session_id, sequence + 1, reply)
        _record_reply_usage(db, reply, session)
        state["reasoning_state"] = merged
        state["evaluation"] = evaluation
        state["clarification_count"] = state.get("clarification_count", 0) + 1
        state["turn_count"] = state.get("turn_count", 1) + 2
        _save_memory(state, reply)
        session.challenge_state_json = json.dumps(state)
        db.commit()
        return {"reply": reply, "turn_count": state["turn_count"], "clarification_count": state["clarification_count"], "evaluation": evaluation, "reasoning_state": merged, "duplicate": False}
    finally:
        lock.release()


@router.post("/{session_id}/coach")
def coach(session_id: int, req: ReviewCoachRequest, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_student_mutation(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")
    duplicate = _idempotent_result(
            db,
            session_id,
            req.client_turn_id,
            "coach",
            {"decision": req.decision},
        )
    if duplicate:
        state = _safe_json(session.challenge_state_json, {})
        reply = duplicate["follow_up"]
        return {
            "duplicate": True,
            "reply": reply,
            "turn_count": state.get("turn_count", 0),
            "coaching_level": state.get("coaching_level", 0),
            "evaluation": state.get("evaluation"),
            "reasoning_state": state.get("reasoning_state", {}),
        }
    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The reviewer is still responding to the previous turn. Please wait for that response.")
    try:
        # Same-process locking is only a fast-fail optimization. The database
        # row lock is the authoritative serializer across application replicas.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session
        _authorize_session_student_mutation(db, session, auth_context(request))
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        # Re-check idempotency while holding the authoritative database lock.
        duplicate = _idempotent_result(
            db,
            session_id,
            req.client_turn_id,
            "coach",
            {"decision": req.decision},
        )
        if duplicate:
            state = _safe_json(session.challenge_state_json, {})
            reply = duplicate["follow_up"]
            return {
                "duplicate": True,
                "reply": reply,
                "turn_count": state.get("turn_count", 0),
                "coaching_level": state.get("coaching_level", 0),
                "evaluation": state.get("evaluation"),
                "reasoning_state": state.get("reasoning_state", {}),
            }

        state = _safe_json(session.challenge_state_json, {})
        challenge = _challenge_from_state(state)
        level = min(state.get("coaching_level", 0) + 1, 5)
        student = _student_for_session(db, session)
        turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
        text = "I need another nudge. If we are going in circles, teach me the concept directly and show me where I can review it."
        reply, merged, evaluation = engine.converse(
            challenge, text, state.get("reasoning_state") or {}, intent="coach", decision=req.decision,
            coaching_level=level, evidence_context=_evidence_context(db, state), conversation_history=_history_payload(turns),
            conversation_memory=state.get("conversation_memory") or {}, student_name=student.display_name if student else "",
        )
        sequence = (turns[-1].sequence if turns else 0) + 1
        db.add(ReviewTurn(
            session_id=session_id, sequence=sequence, client_turn_id=req.client_turn_id,
            actor="student", lens="conversation", content=text, evidence_refs_json="[]",
            signals_json=json.dumps({
                "kind": "student_coach_request",
                "selected_intent": "coach",
                "idempotency_operation": "coach",
                "decision": req.decision,
                "idempotency_fingerprint": _idempotency_fingerprint(
                    {"decision": req.decision}
                ),
                "client_turn_id": req.client_turn_id,
            }),
        ))
        _add_reviewer_turn(db, session_id, sequence + 1, reply)
        _record_reply_usage(db, reply, session)
        state["coaching_level"] = level
        state["reasoning_state"] = merged
        state["evaluation"] = evaluation
        state["turn_count"] = state.get("turn_count", 1) + 2
        _save_memory(state, reply)
        session.challenge_state_json = json.dumps(state)
        db.commit()
        return {"reply": reply, "turn_count": state["turn_count"], "coaching_level": level, "evaluation": evaluation, "reasoning_state": merged, "duplicate": False}
    finally:
        lock.release()


@router.post("/{session_id}/respond")
def respond(session_id: int, req: ReviewResponseRequest, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_student_mutation(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")

    duplicate = _idempotent_result(
            db,
            session_id,
            req.client_turn_id,
            "respond",
            {
                "response": req.response,
                "evidence_refs": list(req.evidence_refs),
                "decision": req.decision,
                "intent": req.intent,
            },
        )
    if duplicate:
        state = _safe_json(session.challenge_state_json, {})
        return {**duplicate, "evaluation": state.get("evaluation"), "turn_count": state.get("turn_count", 0)}

    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The reviewer is still responding to the previous turn. Please wait for that response.")
    try:
        # The process-local lock is only a same-process fast-fail optimization.
        # Correctness across independent application replicas is enforced by
        # the database row lock below.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session

        # Re-evaluate authorization and mutable session state after acquiring
        # the database lock because another replica may have committed changes
        # while this request was waiting.
        _authorize_session_student_mutation(db, session, auth_context(request))
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        # Re-check the database idempotency key while holding the authoritative
        # lock. A competing replica may have completed this logical turn first.
        duplicate = _idempotent_result(
            db,
            session_id,
            req.client_turn_id,
            "respond",
            {
                "response": req.response,
                "evidence_refs": list(req.evidence_refs),
                "decision": req.decision,
                "intent": req.intent,
            },
        )
        if duplicate:
            state = _safe_json(session.challenge_state_json, {})
            return {
                **duplicate,
                "evaluation": state.get("evaluation"),
                "turn_count": state.get("turn_count", 0),
            }

        state = _safe_json(session.challenge_state_json, {})
        challenge = _challenge_from_state(state)
        turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
        sequence = (turns[-1].sequence if turns else 0) + 1
        student = _student_for_session(db, session)
        prior = state.get("reasoning_state") or {}

        follow_up, merged, evaluation = engine.converse(
            challenge, req.response, prior, intent=req.intent, decision=req.decision,
            evidence_refs=req.evidence_refs, coaching_level=state.get("coaching_level", 0),
            evidence_context=_evidence_context(db, state), conversation_history=_history_payload(turns),
            conversation_memory=state.get("conversation_memory") or {},
            student_name=student.display_name if student else "",
        )

        db.add(ReviewTurn(
            session_id=session_id, sequence=sequence, client_turn_id=req.client_turn_id,
            actor="student", lens="conversation",
            content=req.response, evidence_refs_json=json.dumps(req.evidence_refs),
            signals_json=json.dumps({
                **evaluation, "decision": req.decision, "selected_intent": req.intent,
                "idempotency_operation": "respond",
                "idempotency_fingerprint": _idempotency_fingerprint({
                    "response": req.response,
                    "evidence_refs": list(req.evidence_refs),
                    "decision": req.decision,
                    "intent": req.intent,
                }),
                "interpreted_intent": follow_up.get("interpreted_intent"), "client_turn_id": req.client_turn_id,
            }),
        ))
        _add_reviewer_turn(db, session_id, sequence + 1, follow_up)
        _record_reply_usage(db, follow_up, session)

        state["evaluation"] = evaluation
        state["reasoning_state"] = merged
        state["last_follow_up"] = follow_up
        state["last_student_position"] = {"response": req.response, "decision": req.decision, "evidence_refs": req.evidence_refs}
        state["turn_count"] = state.get("turn_count", 1) + 2
        _save_memory(state, follow_up)
        session.challenge_state_json = json.dumps(state)
        db.commit()
        return {"evaluation": evaluation, "follow_up": follow_up, "turn_count": state["turn_count"], "duplicate": False}
    finally:
        lock.release()


@router.post("/{session_id}/evidence-dispute")
def evidence_dispute(session_id: int, req: EvidenceDisputeRequest, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_student_mutation(db, session, auth_context(request))

    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(
            409,
            "The reviewer is still responding to the previous turn. Please wait for that response.",
        )

    try:
        # Process-local locking is only a same-process fast-fail optimization.
        # Database row locking provides authoritative serialization across
        # independent application replicas.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session

        # Authorization and mutable state must be re-evaluated after waiting
        # for another replica's transaction to finish.
        _authorize_session_student_mutation(db, session, auth_context(request))
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        state = _safe_json(session.challenge_state_json, {})
        snapshot_id = state.get("evidence_snapshot_id")
        if not snapshot_id:
            raise HTTPException(
                409,
                "No frozen snapshot is attached to this review",
            )

        # Evidence disputes can change ReviewFindingState, which is shared by
        # every review session attached to the same frozen snapshot. Acquire
        # the snapshot row lock after the session lock so transcript ordering
        # and shared finding-state mutation are both serialized.
        snapshot = (
            db.execute(_evidence_snapshot_for_update_stmt(snapshot_id))
            .scalar_one_or_none()
        )
        if not snapshot:
            raise HTTPException(
                409,
                "No frozen snapshot is attached to this review",
            )

        # Authority may have changed while waiting for the snapshot lock.
        _authorize_session_student_mutation(db, session, auth_context(request))

        evidence = _safe_json(snapshot.summary_json, {})

        path = req.path.strip().lstrip("/")
        artifact = next(
            (
                a
                for a in evidence.get("artifacts", [])
                if a.get("path") == path
            ),
            None,
        )

        # A repeated client_turn_id represents the same logical browser
        # request. Because the ReviewSession row lock is already held, another
        # replica cannot race this lookup and insert the same logical dispute.
        if req.client_turn_id:
            existing_student = (
                db.query(ReviewTurn)
                .filter_by(
                    session_id=session_id,
                    client_turn_id=req.client_turn_id,
                )
                .first()
            )

            if existing_student:
                existing_signals = _safe_json(
                    existing_student.signals_json,
                    {},
                )

                original_path = str(
                    existing_signals.get("path") or ""
                )
                original_explanation = str(
                    existing_signals.get("explanation") or ""
                )
                original_finding_id = existing_signals.get(
                    "requested_finding_id"
                )

                # An idempotency key must never silently alias two different
                # logical requests.
                if (
                    original_path != path
                    or original_explanation != req.explanation
                    or original_finding_id != req.finding_id
                ):
                    raise HTTPException(
                        409,
                        "client_turn_id was already used for a different "
                        "evidence dispute",
                    )

                reviewer_turn = (
                    db.query(ReviewTurn)
                    .filter(
                        ReviewTurn.session_id == session_id,
                        ReviewTurn.sequence > existing_student.sequence,
                        ReviewTurn.actor == "reviewer",
                    )
                    .order_by(ReviewTurn.sequence)
                    .first()
                )

                if not reviewer_turn:
                    raise HTTPException(
                        409,
                        "The previously recorded evidence dispute is "
                        "incomplete",
                    )

                recorded_dispute = next(
                    (
                        item
                        for item in reversed(
                            state.get("evidence_disputes") or []
                        )
                        if item.get("client_turn_id")
                        == req.client_turn_id
                    ),
                    None,
                )

                reviewer_signals = _safe_json(
                    reviewer_turn.signals_json,
                    {},
                )
                duplicate_reply = {
                    "text": reviewer_turn.content,
                    "lens": reviewer_turn.lens,
                    "reviewer": reviewer_signals.get("reviewer"),
                    "provider": reviewer_signals.get("provider"),
                    "model": reviewer_signals.get("model"),
                    "kind": reviewer_signals.get("kind"),
                    "target_move": reviewer_signals.get(
                        "target_move"
                    ),
                    "guidance_refs": reviewer_signals.get(
                        "guidance_refs",
                        [],
                    ),
                    "teach_back": reviewer_signals.get(
                        "teach_back",
                        False,
                    ),
                    "evidence_refs": _safe_json(
                        reviewer_turn.evidence_refs_json,
                        [],
                    ),
                }

                return {
                    "duplicate": True,
                    "disposition": (
                        recorded_dispute.get("disposition")
                        if recorded_dispute
                        else (
                            "artifact_found"
                            if artifact
                            else "not_in_snapshot"
                        )
                    ),
                    "artifact": artifact,
                    "reply": duplicate_reply,
                }

        turns = (
            db.query(ReviewTurn)
            .filter_by(session_id=session_id)
            .order_by(ReviewTurn.sequence)
            .all()
        )
        sequence = (turns[-1].sequence if turns else 0) + 1

        db.add(
            ReviewTurn(
                session_id=session_id,
                sequence=sequence,
                client_turn_id=req.client_turn_id,
                actor="student",
                lens="evidence_dispute",
                content=(
                    f"Evidence dispute: {path} — {req.explanation}"
                ),
                evidence_refs_json=json.dumps([f"PATH:{path}"]),
                signals_json=json.dumps(
                    {
                        "kind": "evidence_dispute",
                        "idempotency_operation": "evidence_dispute",
                        "client_turn_id": req.client_turn_id,
                        "path": path,
                        "explanation": req.explanation,
                        "requested_finding_id": req.finding_id,
                    }
                ),
            )
        )

        reviewer = reviewer_profile("evidence_auditor")
        finding_id = (
            req.finding_id
            or (
                (state.get("challenge") or {}).get("finding") or {}
            ).get("id")
            or next(
                iter(state.get("requested_finding_ids") or []),
                state.get("requested_finding_id"),
            )
        )

        if artifact:
            text = (
                f"Good catch. `{path}` is in the frozen snapshot, so the board should consider it. "
                f"I see it as {artifact.get('provenance','UNKNOWN').lower().replace('_',' ')} "
                f"evidence with quality `{artifact.get('quality','unknown')}`. "
                "That may change the finding. I have recorded your dispute rather than treating "
                "the original review statement as unquestionable. "
                "Now let's test whether the artifact actually supports the claim you say it supports."
            )
            disposition = "artifact_found"

            if finding_id:
                _upsert_finding_state(
                    db,
                    team_id=session.team_id,
                    snapshot_id=snapshot.id,
                    finding_id=finding_id,
                    status="evidence_disputed",
                    user_id=session.user_id,
                    evidence_path=path,
                    rationale=req.explanation,
                )
        else:
            text = (
                f"I checked the frozen snapshot used for this review and `{path}` is not in it. "
                "That does not prove the evidence never existed; it means this review baseline "
                "cannot see it. If the repository changed after the snapshot, we should refresh "
                "evidence rather than argue from two different baselines."
            )
            disposition = "not_in_snapshot"

        payload = {
            "text": text,
            "lens": "evidence_auditor",
            "reviewer": reviewer,
            "provider": "deterministic",
            "kind": "evidence dispute",
            "evidence_refs": [f"PATH:{path}"],
        }

        _add_reviewer_turn(
            db,
            session_id,
            sequence + 1,
            payload,
        )

        state.setdefault("evidence_disputes", []).append(
            {
                "path": path,
                "explanation": req.explanation,
                "disposition": disposition,
                "client_turn_id": req.client_turn_id,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        state["turn_count"] = state.get("turn_count", 1) + 2
        session.challenge_state_json = json.dumps(state)

        db.commit()

        return {
            "duplicate": False,
            "disposition": disposition,
            "artifact": artifact,
            "reply": payload,
        }
    finally:
        lock.release()



@router.post("/{session_id}/findings/{finding_id}/disposition")
def finding_disposition(
    session_id: int,
    finding_id: str,
    req: FindingDispositionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")

    ctx = auth_context(request)
    actor_user_id = _authorize_finding_disposition_mutation(
        db, session, ctx, req.status
    )
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")

    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(
            409,
            "The reviewer is still responding to the previous turn. Please wait for that response.",
        )

    try:
        # Finding disposition changes snapshot-scoped lifecycle state, but it is
        # still a ReviewSession mutation. Lock the session first, matching the
        # ordering used by evidence-dispute, so semester archive and concurrent
        # review requests cannot race a stale pre-archive session state.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session
        ctx = auth_context(request)
        actor_user_id = _authorize_finding_disposition_mutation(
            db, session, ctx, req.status
        )
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        state = _safe_json(session.challenge_state_json, {})
        snapshot_id = state.get("evidence_snapshot_id")
        if not snapshot_id:
            raise HTTPException(
                409,
                "No frozen snapshot is attached to this review",
            )

        # Finding state is shared by every review session using this frozen
        # snapshot. Session -> snapshot is the established lock order.
        snapshot = (
            db.execute(_evidence_snapshot_for_update_stmt(snapshot_id))
            .scalar_one_or_none()
        )
        if not snapshot:
            raise HTTPException(
                409,
                "No frozen snapshot is attached to this review",
            )

        # Authority and lifecycle state may have changed while waiting for the
        # snapshot lock. Re-read the session before committing shared state.
        db.refresh(session)
        ctx = auth_context(request)
        actor_user_id = _authorize_finding_disposition_mutation(
            db, session, ctx, req.status
        )
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        _upsert_finding_state(
            db,
            team_id=session.team_id,
            snapshot_id=snapshot.id,
            finding_id=finding_id,
            status=req.status,
            user_id=actor_user_id or session.user_id,
            evidence_path=req.evidence_path,
            rationale=req.rationale,
        )
        db.commit()

        return {
            "finding_id": finding_id,
            "status": req.status,
            "snapshot_id": snapshot.id,
        }
    finally:
        lock.release()



@router.post("/{session_id}/commit")
def commit_position(session_id: int, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_student_mutation(db, session, auth_context(request))

    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(
            409,
            "The reviewer is still responding to the previous turn. Please wait for that response.",
        )

    try:
        # Recommendation recording changes both ReviewTurn ordering and
        # ReviewSession state, so PostgreSQL is the authoritative serializer
        # across independent application replicas.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session

        # Re-check authority and mutable state after any database lock wait.
        _authorize_session_student_mutation(db, session, auth_context(request))
        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        state = _safe_json(session.challenge_state_json, {})
        evaluation = state.get("evaluation") or {}
        position = state.get("last_student_position")

        if not position:
            raise HTTPException(
                409,
                "Discuss a decision before stating a recommendation",
            )
        if not evaluation.get("ready_to_commit"):
            raise HTTPException(
                409,
                "The recommendation still has material reasoning gaps. "
                "Continue the review before recording it.",
            )

        student = _student_for_session(db, session)
        first_name = (
            student.display_name.split(" ")[0]
            if student and student.display_name
            else ""
        )
        profile = reviewer_profile("chief_architect")
        prefix = f"{first_name}, " if first_name else ""
        reply = {
            "lens": "chief_architect",
            "reviewer": profile,
            "kind": "recommendation_confirmation",
            "provider": "deterministic",
            "text": (
                f"{prefix}your recommendation is now defensible enough to record. "
                "The important point is not that the board has declared it permanently correct; "
                "it is that your decision, evidence boundary, consequence, ownership, and closure "
                "condition are visible and challengeable. This records the judgment you are "
                "prepared to defend now. You can revise it when new evidence or better reasoning "
                "changes your view."
            ),
        }

        # An identical retry is idempotent, but a later changed student
        # position remains eligible to become a revised recommendation.
        committed = state.get("committed_position")
        if committed:
            committed_position = {
                key: value
                for key, value in committed.items()
                if key != "committed_at"
            }
            if committed_position == position:
                return {
                    "status": "committed",
                    "position": committed,
                    "reply": reply,
                    "duplicate": True,
                }

        turns = (
            db.query(ReviewTurn)
            .filter_by(session_id=session_id)
            .order_by(ReviewTurn.sequence)
            .all()
        )
        sequence = (turns[-1].sequence if turns else 0) + 1

        _add_reviewer_turn(
            db,
            session_id,
            sequence,
            reply,
        )

        state["committed_position"] = {
            **position,
            "committed_at": datetime.now(timezone.utc).isoformat(),
        }
        state["active_reviewer"] = reply["reviewer"]
        state["turn_count"] = state.get("turn_count", 1) + 1
        session.challenge_state_json = json.dumps(state)

        db.commit()

        return {
            "status": "committed",
            "position": state["committed_position"],
            "reply": reply,
            "duplicate": False,
        }
    finally:
        lock.release()


@router.post("/{session_id}/complete")
def complete(session_id: int, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session_student_mutation(db, session, auth_context(request))

    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(
            409,
            "The reviewer is still responding to the previous turn. Please wait for that response.",
        )

    try:
        # Completion participates in the same authoritative database locking
        # protocol as every other ReviewSession mutation.
        locked_session = (
            db.execute(_review_session_for_update_stmt(session_id))
            .scalar_one_or_none()
        )
        if not locked_session:
            raise HTTPException(404, "Review session not found")

        session = locked_session

        # Re-check authority after waiting for any competing replica.
        _authorize_session_student_mutation(db, session, auth_context(request))

        # Completion is idempotent. A retry must not rewrite the historical
        # completion timestamp.
        if session.status == "completed":
            return {
                "session_id": session.id,
                "status": session.status,
                "completed_at": (
                    session.completed_at.isoformat()
                    if session.completed_at
                    else None
                ),
            }

        if session.status != "active":
            raise HTTPException(409, "Review session is not active")

        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "session_id": session.id,
            "status": session.status,
            "completed_at": session.completed_at.isoformat(),
        }
    finally:
        lock.release()
