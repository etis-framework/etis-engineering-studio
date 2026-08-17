import json
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import EvidenceSnapshot, ReviewSession, ReviewTurn, Team, User, TeamSection, TeamMembership, ReviewFindingState
from ..schemas import ReviewStartRequest, ReviewResponseRequest, ReviewClarifyRequest, ReviewCoachRequest, EvidenceDisputeRequest, FindingDispositionRequest
from ..services.challenge_engine import ChallengeEngine, Challenge, reviewer_profile, default_memory
from ..services.review_orchestrator import ReviewOrchestrator
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


def _idempotent_result(db: Session, session_id: int, client_turn_id: str | None):
    if not client_turn_id:
        return None
    turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    for idx, turn in enumerate(turns):
        if turn.actor != "student":
            continue
        signals = _safe_json(turn.signals_json, {})
        if signals.get("client_turn_id") == client_turn_id:
            reviewer = next((x for x in turns[idx + 1:] if x.actor == "reviewer"), None)
            if reviewer:
                rs = _safe_json(reviewer.signals_json, {})
                return {
                    "duplicate": True,
                    "follow_up": {
                        "text": reviewer.content, "lens": reviewer.lens, "reviewer": rs.get("reviewer"),
                        "kind": rs.get("kind"), "provider": rs.get("provider"), "model": rs.get("model"),
                        "target_move": rs.get("target_move"), "guidance_refs": rs.get("guidance_refs", []),
                        "teach_back": rs.get("teach_back", False),
                    },
                }
    return None


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




def _authorize_session(
    db: Session,
    session: ReviewSession,
    ctx: dict,
):
    if ctx.get("role") == "developer":
        return

    # A student always retains access to their own Review Room conversation.
    if session.user_id == ctx.get("uid"):
        return

    # Access to another student's review requires current database-backed
    # teaching-staff authority for the team's section. A stale role embedded
    # in an unexpired session token is not sufficient.
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
            # No current teaching-staff authority: self-service only. This
            # deliberately ignores any stale staff role embedded in the token.
            user_id = caller_user_id

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


@router.post("/start")
def start(req: ReviewStartRequest, request:Request, db: Session = Depends(get_db)):
    ctx = auth_context(request)
    team = require_team_access(db, ctx, req.team_id)

    # Selecting another person as the subject of a Review Room session is
    # privileged authority. Derive that authority from current database state,
    # never from a staff role embedded in an already-issued session token.
    can_select_review_subject = ctx.get("role") == "developer"

    if not can_select_review_subject:
        section_ids = accessible_section_ids(db, ctx)

        if section_ids is None:
            # Active course-owner authority is intentionally global.
            can_select_review_subject = True
        else:
            section_link = (
                db.query(TeamSection)
                .filter_by(team_id=team.id)
                .first()
            )
            can_select_review_subject = bool(
                section_link
                and section_link.section_id in section_ids
            )

    if not can_select_review_subject:
        # The authenticated caller is authoritative. A stale staff token must
        # not preserve the ability to create a review attributed to another
        # team member.
        req.user_id = ctx.get("uid")

        if not db.query(TeamMembership).filter_by(
            team_id=team.id,
            user_id=req.user_id,
        ).first():
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this team",
            )

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
        "evidence_disputes": [],
    }

    session = ReviewSession(
        team_id=team.id,
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

    challenge_payload = challenge.to_dict()
    challenge_payload["opening_text"] = opening["text"]
    return {
        "session_id": session.id,
        "team": {"id": team.id, "name": team.name, "project_name": team.project_name, "phase": req.phase_id},
        "user": {"id": user.id, "name": user.display_name, "role": user.role},
        "challenge": challenge_payload,
        "evidence": evidence_payload,
        "evidence_cache_reused": bool(state.get("evidence_cache_reused")),
    }


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
    _authorize_session(db, session, auth_context(request))
    turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    state = _safe_json(session.challenge_state_json, {})
    snapshot = db.get(EvidenceSnapshot, state.get("evidence_snapshot_id")) if state.get("evidence_snapshot_id") else None
    evidence = _safe_json(snapshot.summary_json, {}) if snapshot else None
    if snapshot and evidence:
        evidence=_decorate_finding_states(evidence,_finding_states(db,snapshot.id))
    user = _student_for_session(db, session)
    return {
        "session": {
            "id": session.id,
            "phase_id": session.phase_id,
            "status": session.status,
            "mode": session.mode,
            "started_at": session.started_at.isoformat(),
            "student": {"id": user.id, "name": user.display_name, "role": user.role} if user else None,
        },
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
            }
            for turn in turns
        ],
    }


@router.post("/{session_id}/clarify")
def clarify(session_id: int, req: ReviewClarifyRequest, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")
    duplicate = _idempotent_result(db, session_id, req.client_turn_id)
    if duplicate:
        state = _safe_json(session.challenge_state_json, {})
        return {**duplicate, "evaluation": state.get("evaluation"), "reasoning_state": state.get("reasoning_state", {})}
    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The reviewer is still responding to the previous turn. Please wait for that response.")
    try:
        duplicate = _idempotent_result(db, session_id, req.client_turn_id)
        if duplicate:
            state = _safe_json(session.challenge_state_json, {})
            return {**duplicate, "evaluation": state.get("evaluation"), "reasoning_state": state.get("reasoning_state", {})}
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
            session_id=session_id, sequence=sequence, actor="student", lens="conversation", content=req.question,
            evidence_refs_json="[]", signals_json=json.dumps({
                "kind": "student_conversation", "selected_intent": "clarify",
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
    _authorize_session(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")
    duplicate = _idempotent_result(db, session_id, req.client_turn_id)
    if duplicate:
        state = _safe_json(session.challenge_state_json, {})
        return {**duplicate, "evaluation": state.get("evaluation"), "reasoning_state": state.get("reasoning_state", {})}
    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The reviewer is still responding to the previous turn. Please wait for that response.")
    try:
        duplicate = _idempotent_result(db, session_id, req.client_turn_id)
        if duplicate:
            state = _safe_json(session.challenge_state_json, {})
            return {**duplicate, "evaluation": state.get("evaluation"), "reasoning_state": state.get("reasoning_state", {})}
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
            session_id=session_id, sequence=sequence, actor="student", lens="conversation", content=text, evidence_refs_json="[]",
            signals_json=json.dumps({"kind": "student_coach_request", "selected_intent": "coach", "client_turn_id": req.client_turn_id}),
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
    _authorize_session(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")

    duplicate = _idempotent_result(db, session_id, req.client_turn_id)
    if duplicate:
        state = _safe_json(session.challenge_state_json, {})
        return {**duplicate, "evaluation": state.get("evaluation"), "turn_count": state.get("turn_count", 0)}

    lock = _session_lock(session_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The reviewer is still responding to the previous turn. Please wait for that response.")
    try:
        # Check again after acquiring the lock in case an HTTP retry arrived as the first request completed.
        duplicate = _idempotent_result(db, session_id, req.client_turn_id)
        if duplicate:
            state = _safe_json(session.challenge_state_json, {})
            return {**duplicate, "evaluation": state.get("evaluation"), "turn_count": state.get("turn_count", 0)}

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
            session_id=session_id, sequence=sequence, actor="student", lens="conversation",
            content=req.response, evidence_refs_json=json.dumps(req.evidence_refs),
            signals_json=json.dumps({
                **evaluation, "decision": req.decision, "selected_intent": req.intent,
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
    _authorize_session(db, session, auth_context(request))
    state = _safe_json(session.challenge_state_json, {})
    snapshot = db.get(EvidenceSnapshot, state.get("evidence_snapshot_id"))
    evidence = _safe_json(snapshot.summary_json, {}) if snapshot else {}
    path = req.path.strip().lstrip('/')
    artifact = next((a for a in evidence.get("artifacts", []) if a.get("path") == path), None)
    turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    sequence = (turns[-1].sequence if turns else 0) + 1
    db.add(ReviewTurn(session_id=session_id, sequence=sequence, actor="student", lens="evidence_dispute", content=f"Evidence dispute: {path} — {req.explanation}", evidence_refs_json=json.dumps([f"PATH:{path}"]), signals_json=json.dumps({"kind": "evidence_dispute"})))
    reviewer = reviewer_profile("evidence_auditor")
    finding_id=req.finding_id or ((state.get("challenge") or {}).get("finding") or {}).get("id") or next(iter(state.get("requested_finding_ids") or []), state.get("requested_finding_id"))
    if artifact:
        text = (
            f"Good catch. `{path}` is in the frozen snapshot, so the board should consider it. "
            f"I see it as {artifact.get('provenance','UNKNOWN').lower().replace('_',' ')} evidence with quality `{artifact.get('quality','unknown')}`. "
            "That may change the finding. I have recorded your dispute rather than treating the original review statement as unquestionable. "
            "Now let's test whether the artifact actually supports the claim you say it supports."
        )
        disposition = "artifact_found"
        if finding_id:
            _upsert_finding_state(db,team_id=session.team_id,snapshot_id=snapshot.id,finding_id=finding_id,status="evidence_disputed",user_id=session.user_id,evidence_path=path,rationale=req.explanation)
    else:
        text = (
            f"I checked the frozen snapshot used for this review and `{path}` is not in it. That does not prove the evidence never existed; "
            "it means this review baseline cannot see it. If the repository changed after the snapshot, we should refresh evidence rather than argue from two different baselines."
        )
        disposition = "not_in_snapshot"
    payload = {"text": text, "lens": "evidence_auditor", "reviewer": reviewer, "provider": "deterministic", "kind": "evidence dispute", "evidence_refs": [f"PATH:{path}"]}
    _add_reviewer_turn(db, session_id, sequence + 1, payload)
    state.setdefault("evidence_disputes", []).append({"path": path, "explanation": req.explanation, "disposition": disposition, "at": datetime.now(timezone.utc).isoformat()})
    state["turn_count"] = state.get("turn_count", 1) + 2
    session.challenge_state_json = json.dumps(state)
    db.commit()
    return {"disposition": disposition, "artifact": artifact, "reply": payload}


@router.post("/{session_id}/findings/{finding_id}/disposition")
def finding_disposition(session_id:int, finding_id:str, req:FindingDispositionRequest, request:Request, db:Session=Depends(get_db)):
    session=db.get(ReviewSession,session_id)
    if not session: raise HTTPException(404,"Review session not found")
    ctx=auth_context(request)
    _authorize_session(db, session, ctx)
    state=_safe_json(session.challenge_state_json,{})
    snapshot=db.get(EvidenceSnapshot,state.get("evidence_snapshot_id"))
    if not snapshot: raise HTTPException(409,"No frozen snapshot is attached to this review")
    # Students may express disposition and risk decisions, but they cannot
    # unilaterally declare a board finding confirmed/corrected/resolved. Those
    # states require current database-backed teaching-staff authority or the
    # local developer identity.
    if req.status in {"confirmed", "corrected", "resolved"}:
        if ctx.get("role") != "developer":
            section_link = (
                db.query(TeamSection)
                .filter_by(team_id=session.team_id)
                .first()
            )
            if not section_link:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "This finding state requires board evidence validation "
                        "or teaching-staff action"
                    ),
                )

            require_section_role(
                db,
                ctx,
                section_link.section_id,
                STAFF_ROLES,
            )
    _upsert_finding_state(db,team_id=session.team_id,snapshot_id=snapshot.id,finding_id=finding_id,status=req.status,user_id=session.user_id,evidence_path=req.evidence_path,rationale=req.rationale)
    db.commit()
    return {"finding_id":finding_id,"status":req.status,"snapshot_id":snapshot.id}


@router.post("/{session_id}/commit")
def commit_position(session_id: int, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session(db, session, auth_context(request))
    if session.status != "active":
        raise HTTPException(409, "Review session is not active")

    state = _safe_json(session.challenge_state_json, {})
    evaluation = state.get("evaluation") or {}
    position = state.get("last_student_position")
    if not position:
        raise HTTPException(409, "Discuss a decision before stating a recommendation")
    if not evaluation.get("ready_to_commit"):
        raise HTTPException(409, "The recommendation still has material reasoning gaps. Continue the review before recording it.")

    student = _student_for_session(db, session)
    first_name = (student.display_name.split(" ")[0] if student and student.display_name else "")
    profile = reviewer_profile("chief_architect")
    prefix = f"{first_name}, " if first_name else ""
    reply = {
        "lens": "chief_architect",
        "reviewer": profile,
        "kind": "recommendation_confirmation",
        "provider": "deterministic",
        "text": (
            f"{prefix}your recommendation is now defensible enough to record. The important point is not that the board has declared it permanently correct; "
            "it is that your decision, evidence boundary, consequence, ownership, and closure condition are visible and challengeable. "
            "This records the judgment you are prepared to defend now. You can revise it when new evidence or better reasoning changes your view."
        ),
    }
    turns = db.query(ReviewTurn).filter_by(session_id=session_id).order_by(ReviewTurn.sequence).all()
    sequence = (turns[-1].sequence if turns else 0) + 1
    _add_reviewer_turn(db, session_id, sequence, reply)
    state["committed_position"] = {**position, "committed_at": datetime.now(timezone.utc).isoformat()}
    state["active_reviewer"] = reply["reviewer"]
    state["turn_count"] = state.get("turn_count", 1) + 1
    session.challenge_state_json = json.dumps(state)
    db.commit()
    return {"status": "committed", "position": state["committed_position"], "reply": reply}


@router.post("/{session_id}/complete")
def complete(session_id: int, request:Request, db: Session = Depends(get_db)):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, "Review session not found")
    _authorize_session(db, session, auth_context(request))
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"session_id": session.id, "status": session.status, "completed_at": session.completed_at.isoformat()}
