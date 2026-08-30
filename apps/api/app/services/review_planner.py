from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Mapping, Sequence

from .ai_provider import OpenAIResponsesProvider
from .model_disclosure import sanitize_model_text
from .review_planning import (
    CandidateMoveType,
    CandidateNextMove,
    CandidateRejectionCode,
    ObjectiveOutcome,
    PlanningContext,
    PlanningNeed,
    SelectionReasonCode,
    SelectionResult,
)
from .next_question_selector import (
    NextQuestionSelector,
    allowed_evidence_refs,
    candidate_addresses_need,
    context_requires_teaching,
    reasoning_dimension_for_outcome,
    resolve_primary_need,
)


PLANNING_SHADOW_SCHEMA_VERSION = 1
_ALLOWED_REVIEWER_LENSES = frozenset(
    {"evidence_auditor", "chief_architect", "delivery", "red_team"}
)

@dataclass(frozen=True)
class PlanningShadowOutcome:
    signal: dict[str, Any]
    shadow_state: dict[str, Any]
    usage_events: tuple[dict[str, Any], ...] = ()


def blank_planning_shadow() -> dict[str, Any]:
    return {
        "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
        "comparison": {
            "completed_plans": 0,
            "skipped_plans": 0,
            "failed_plans": 0,
            "candidates_considered": 0,
            "candidates_rejected": 0,
            "same_target_as_legacy": 0,
            "different_target_from_legacy": 0,
            "realization_failures": 0,
            "realization_repair_attempts": 0,
            "realization_repair_successes": 0,
        },
        "last_plan": None,
    }


def ensure_planning_shadow(value: Mapping[str, Any] | None) -> dict[str, Any]:
    base = blank_planning_shadow()
    incoming = dict(value or {})
    comparison = incoming.get("comparison") or {}
    for key in base["comparison"]:
        try:
            base["comparison"][key] = max(0, int(comparison.get(key, 0)))
        except (TypeError, ValueError):
            base["comparison"][key] = 0
    if isinstance(incoming.get("last_plan"), Mapping):
        base["last_plan"] = dict(incoming["last_plan"])
    return base


class ReviewPlanner:
    """Shadow planner + deterministic selector + bounded move realizer.

    The semantic planner proposes engineering moves only. The application-owned
    selector chooses one move. Only then may a separate semantic realizer phrase
    that locked move as a comparison prompt. Neither model call receives the
    current engine's newly generated reply, so current-vs-shadow comparison does
    not copy the production-selected question.
    """

    def __init__(self, ai=None, selector=None):
        self.ai = ai or OpenAIResponsesProvider()
        self.selector = selector or NextQuestionSelector()

    def plan_turn(
        self,
        *,
        context: PlanningContext,
        shadow_state: Mapping[str, Any] | None,
        current_engine: Mapping[str, Any],
        turn_sequence: int,
        client_turn_id: str | None,
        operation: str,
    ) -> PlanningShadowOutcome:
        shadow = ensure_planning_shadow(shadow_state)

        if operation == "coach":
            return _skipped_outcome(
                shadow,
                reason="synthetic_coach_request",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
            )
        if not context.objective.required_outcomes and not context.objective.optional_outcomes:
            return _skipped_outcome(
                shadow,
                reason="objective_has_no_plannable_outcomes",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
            )
        if not _planner_available(self.ai):
            return _failed_outcome(
                shadow,
                error_type="PlannerUnavailable",
                failure_stage="planner",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
            )

        usage_events: list[dict[str, Any]] = []
        try:
            planned = self.ai.plan_review_turn(_planner_system_prompt(), _planner_user_prompt(context))
        except Exception as exc:
            return _failed_outcome(
                shadow,
                error_type=type(exc).__name__,
                failure_stage="planner",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
            )
        _append_usage(usage_events, planned)

        semantic_need, candidates = _normalize_planner_result(planned)
        primary_need, primary_need_source = resolve_primary_need(context, semantic_need)
        candidates = _ensure_bounded_fallback_candidates(
            context, candidates, primary_need=primary_need
        )
        selection, rejected = self.selector.select(
            context=context, candidates=candidates, semantic_need=semantic_need
        )
        if selection is None:
            signal = {
                "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
                "status": "failed",
                "failure_stage": "selector",
                "error_type": "NoSelectableCandidate",
                "turn_sequence": turn_sequence,
                "client_turn_id": client_turn_id,
                "operation": operation,
                "semantic_primary_need": semantic_need.value if semantic_need else None,
                "primary_need": primary_need.value if primary_need else None,
                "primary_need_source": primary_need_source.value if primary_need_source else None,
                "candidate_count": len(candidates),
                "candidate_moves": [item.to_dict() for item in candidates],
                "rejected_candidates": [item.to_dict() for item in rejected],
            }
            return PlanningShadowOutcome(
                signal=signal,
                shadow_state=_update_shadow(
                    shadow,
                    signal,
                    status="failed",
                    candidate_count=len(candidates),
                    rejected_count=len(rejected),
                ),
                usage_events=tuple(usage_events),
            )

        selected = next(
            candidate for candidate in candidates if candidate.candidate_id == selection.selected_candidate_id
        )
        if not _realizer_available(self.ai):
            return _failed_after_selection(
                shadow,
                usage_events=usage_events,
                selection=selection,
                candidates=candidates,
                error_type="RealizerUnavailable",
                failure_stage="realizer",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
            )

        realization_repair_attempted = False
        realization_repair_succeeded = False
        initial_realization_rejections: tuple[CandidateRejectionCode, ...] = ()
        try:
            realized = self.ai.realize_review_move(
                _realizer_system_prompt(),
                _realizer_user_prompt(context, selected, selection),
            )
        except Exception as exc:
            return _failed_after_selection(
                shadow,
                usage_events=usage_events,
                selection=selection,
                candidates=candidates,
                error_type=type(exc).__name__,
                failure_stage="realizer",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
            )
        _append_usage(usage_events, realized)

        lead_in, selected_question = _normalize_realization(realized)
        realization_rejections = _realization_rejection_codes(
            context=context,
            candidate=selected,
            lead_in=lead_in,
            question=selected_question,
        )
        if realization_rejections:
            initial_realization_rejections = realization_rejections
            realization_repair_attempted = True
            try:
                repaired = self.ai.realize_review_move(
                    _realizer_repair_system_prompt(realization_rejections),
                    _realizer_user_prompt(
                        context,
                        selected,
                        selection,
                        repair_rejection_codes=realization_rejections,
                    ),
                )
            except Exception as exc:
                return _failed_after_selection(
                    shadow,
                    usage_events=usage_events,
                    selection=selection,
                    candidates=candidates,
                    error_type=type(exc).__name__,
                    failure_stage="realizer_repair",
                    turn_sequence=turn_sequence,
                    client_turn_id=client_turn_id,
                    operation=operation,
                    realization_repair_attempted=True,
                    initial_realization_rejections=initial_realization_rejections,
                )
            _append_usage(usage_events, repaired)
            lead_in, selected_question = _normalize_realization(repaired)
            realization_rejections = _realization_rejection_codes(
                context=context,
                candidate=selected,
                lead_in=lead_in,
                question=selected_question,
            )
            realization_repair_succeeded = not realization_rejections

        if realization_rejections:
            signal = {
                "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
                "status": "failed",
                "failure_stage": "realizer_validation",
                "error_type": "UnsafeOrInvalidRealization",
                "turn_sequence": turn_sequence,
                "client_turn_id": client_turn_id,
                "operation": operation,
                "semantic_primary_need": semantic_need.value if semantic_need else None,
                "primary_need": selection.primary_need.value if selection.primary_need else None,
                "primary_need_source": (
                    selection.primary_need_source.value if selection.primary_need_source else None
                ),
                "candidate_count": len(candidates),
                "candidate_moves": [item.to_dict() for item in candidates],
                "selected_candidate_id": selection.selected_candidate_id,
                "selected_move_type": selection.selected_move_type.value,
                "target_outcome": selection.target_outcome.value,
                "realization_repair": {
                    "attempted": realization_repair_attempted,
                    "succeeded": False,
                    "initial_rejection_codes": [
                        code.value for code in initial_realization_rejections
                    ],
                    "final_rejection_codes": [code.value for code in realization_rejections],
                },
                "realization_rejection_codes": [code.value for code in realization_rejections],
            }
            return PlanningShadowOutcome(
                signal=signal,
                shadow_state=_update_shadow(
                    shadow,
                    signal,
                    status="failed",
                    candidate_count=len(candidates),
                    rejected_count=len(selection.rejected_candidates),
                    realization_failure=True,
                    realization_repair_attempted=realization_repair_attempted,
                    realization_repair_succeeded=False,
                ),
                usage_events=tuple(usage_events),
            )

        proposed_prompt = "\n\n".join(part for part in (lead_in, selected_question) if part).strip()
        legacy_target = str(current_engine.get("target_move") or "")
        legacy_question = _extract_main_question(str(current_engine.get("question") or ""))
        selected_legacy_dimension = reasoning_dimension_for_outcome(selection.target_outcome)
        same_target = bool(
            selected_legacy_dimension and legacy_target == selected_legacy_dimension
        )
        similarity = _question_similarity(legacy_question, selected_question)
        signal = {
            "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
            "status": "completed",
            "turn_sequence": turn_sequence,
            "client_turn_id": client_turn_id,
            "operation": operation,
            "current_engine": {
                "target_move": legacy_target or None,
                "reviewer_lens": str(current_engine.get("reviewer_lens") or "") or None,
                "question": legacy_question,
            },
            "shadow_planner": {
                "semantic_primary_need": semantic_need.value if semantic_need else None,
                "primary_need": selection.primary_need.value if selection.primary_need else None,
                "primary_need_source": (
                    selection.primary_need_source.value if selection.primary_need_source else None
                ),
                "candidate_count": len(candidates),
                "candidate_moves": [item.to_dict() for item in candidates],
                "selected_candidate_id": selection.selected_candidate_id,
                "selected_move_type": selection.selected_move_type.value,
                "target_outcome": selection.target_outcome.value,
                "evidence_refs": list(selected.evidence_refs),
                "selected_reviewer_lens": selection.selected_reviewer_lens,
                "teaching_required": selection.teaching_required,
                "selection_reason_codes": [code.value for code in selection.reason_codes],
                "lead_in": lead_in,
                "proposed_question": selected_question,
                "proposed_prompt": proposed_prompt,
                "realization_repair": {
                    "attempted": realization_repair_attempted,
                    "succeeded": realization_repair_succeeded,
                    "initial_rejection_codes": [
                        code.value for code in initial_realization_rejections
                    ],
                    "final_rejection_codes": [],
                },
                "rejected_candidates": [item.to_dict() for item in selection.rejected_candidates],
            },
            "comparison": {
                "same_target_as_legacy": same_target if selected_legacy_dimension else None,
                "question_similarity": similarity,
            },
        }
        return PlanningShadowOutcome(
            signal=signal,
            shadow_state=_update_shadow(
                shadow,
                signal,
                status="completed",
                candidate_count=len(candidates),
                rejected_count=len(selection.rejected_candidates),
                same_target=same_target if selected_legacy_dimension else None,
                realization_repair_attempted=realization_repair_attempted,
                realization_repair_succeeded=realization_repair_succeeded,
            ),
            usage_events=tuple(usage_events),
        )


def _planner_system_prompt() -> str:
    return """
You are the ETIS shadow Review Planner. You are not the student-facing reviewer, not a
teacher persona, not a grader, and not an engineering authority. Generate a small set of
plausible NEXT ENGINEERING MOVES for an independent application-owned selector.

Authority rules:
1. Stay inside the locked Review Objective and current phase.
2. Use only the supplied frozen evidence package. Never invent a path, finding, test, issue,
   pull request, branch, workflow result, or repository fact.
3. Validated shadow reasoning is context; prior-session reasoning is not current proof.
4. Respect evidence-backed student disagreement and reviewer fallibility.
5. Legitimate uncertainty is a valid engineering state. Do not force false certainty.
6. First classify exactly one `primary_need`: the reasoning problem that matters most **now**,
   not the Review Objective outcome that happens to be next in a list. Use:
   STUDENT_CHALLENGE for an evidence-backed dispute with the reviewer;
   TEACHING_OR_TEACHBACK when the student needs bounded teaching or must explain the work;
   EVIDENCE_DEFICIT for an unsupported/broad claim or missing proof;
   CONTRADICTION_OR_STALE_STATE for conflicting/stale artifacts or self-correction;
   UNCERTAINTY for a legitimate unresolved unknown;
   INDEPENDENT_JUDGMENT for blind reviewer/AI deference; POSITION_CLARITY for a vague position;
   ACTION_OR_CHANGE for the next bounded action/owner/change condition; STRESS_TEST for testing
   an otherwise defensible position; CONSEQUENCE for a still-missing material implication; and
   SYNTHESIS only when the current reasoning is genuinely ready to close or summarize.
7. Generate candidates that address that primary need before secondary agenda items.
8. Continue from what the student has already established. Do not propose CLARIFY_CONSEQUENCE
   as the leading move when the newest student turn already states a meaningful consequence or
   decision risk. Resolve the more immediate analytical defect instead.
9. Treat these first-order defects as higher-value than generic consequence elaboration when they
   are present in the student's newest turn:
   - unsupported/broad claim or missing proof -> TEST_EVIDENCE_BOUNDARY or REQUEST_MISSING_EVIDENCE;
   - stale/conflicting artifacts or self-correction -> RECONCILE_CONTRADICTION,
     CLARIFY_ACTION_BOUNDARY, or ESTABLISH_CHANGE_TRIGGER;
   - legitimate unknown -> SURFACE_UNCERTAINTY, REQUEST_MISSING_EVIDENCE, or
     ESTABLISH_CHANGE_TRIGGER without forcing certainty;
   - blind deference to reviewer/AI or inability to explain AI-assisted work ->
     MAKE_POSITION_EXPLICIT, TEACH_CONCEPT, or REQUEST_TEACH_BACK as appropriate.
10. Evidence-testing candidates should cite the relevant supplied frozen evidence refs when the
   move depends on known evidence. Do not omit a valid ref merely to make a generic candidate.
11. Required Review Objective outcomes are boundaries, not a checklist order. Do not propose a move
   merely because an outcome is still unresolved if it would repeat or skip over the student's
   actual reasoning need.
12. Prefer consequential, evidence-grounded, novel moves over terminology trivia or artifact theater.
13. Do not ask for future-phase deliverables.
14. If the student needs direct teaching, propose TEACH_CONCEPT or REQUEST_TEACH_BACK before
   continuing ordinary challenge moves.
15. Return 2-4 genuinely distinct candidates when possible, ordered from highest to lowest value.
   Each candidate targets exactly one listed objective outcome and uses only allowed move types.
16. Do NOT draft the student-facing question. A separate realizer runs only after the
    application selector locks one move.
17. Candidate reason codes are descriptive hints only; the application independently selects.
18. Do not reveal chain-of-thought. Return only the required structured output.
""".strip()


def _planner_user_prompt(context: PlanningContext) -> str:
    validated = context.validated_reasoning_state or {}
    dimensions = validated.get("dimensions") if isinstance(validated, Mapping) else {}
    reasoning_status = {
        str(key): str((value or {}).get("status") or "unestablished")
        for key, value in (dimensions or {}).items()
        if isinstance(value, Mapping)
    }
    payload = {
        "phase_id": context.phase_id,
        "review_mode": context.review_mode.value,
        "review_objective": context.objective.to_dict(),
        "frozen_commit_sha": context.commit_sha,
        "frozen_evidence_package": context.evidence_package,
        "validated_shadow_reasoning": reasoning_status,
        "current_findings": list(context.current_findings),
        "finding_states": list(context.finding_states),
        "focus": context.focus,
        "recent_questions_before_current_engine_reply": list(context.recent_questions[-8:]),
        "recent_student_turns": list(context.recent_student_turns[-8:]),
        "latest_student_turn": context.latest_student_turn,
        "latest_student_evidence_refs": list(context.latest_student_evidence_refs),
        "reviewer_corrections": list(context.reviewer_corrections),
        "evidence_disputes": list(context.evidence_disputes),
        "explicit_uncertainty": list(context.explicit_uncertainty),
        "current_position": context.current_position,
        "committed_position": context.committed_position,
        "coaching_level": context.coaching_level,
        "assistance_state": context.assistance_state,
        "active_reviewer_lens": context.active_reviewer_lens,
    }
    return sanitize_model_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))[:14000]
    ).text


def _realizer_system_prompt() -> str:
    return """
You are the ETIS shadow move realizer. The Review Planner has already proposed candidates and
an application-owned selector has LOCKED exactly one engineering move. You may phrase that
move naturally, but you may not re-plan, change the target outcome, invent evidence, add a
second analytical agenda, grade the student, or decide engineering truth.

Rules:
1. Stay inside the locked move, Review Objective, current phase, and supplied frozen evidence.
2. Never invent repository evidence or imply an artifact proves more than supplied context supports.
3. Respect evidence-backed student disagreement and reviewer fallibility.
4. Ask exactly one main question. Do not ask compound multi-question interrogations.
5. Do not demand future-phase artifacts or generic terminology recitation.
6. If teaching_required is false, lead_in should be empty or a brief acknowledgement (<=45 words).
7. If teaching_required is true, lead_in may briefly teach the needed concept (<=90 words), then
   the question should be a short teach-back/application question.
8. Match the selected reviewer lens when one is supplied; otherwise preserve the active reviewer.
9. Do not expose scores, hidden state, reason codes, chain-of-thought, or shadow-mode mechanics.
10. Return only the required structured fields.
""".strip()


def _realizer_repair_system_prompt(
    rejection_codes: Sequence[CandidateRejectionCode],
) -> str:
    codes = ", ".join(code.value for code in rejection_codes)
    return (
        _realizer_system_prompt()
        + "\n\nThe previous wording was rejected by deterministic validation for: "
        + codes
        + ". Repair the wording ONCE while preserving the exact locked move, target outcome, "
          "evidence boundary, and reviewer lens. Do not re-plan. Do not name a later A-phase when "
          "the rejection is FUTURE_PHASE_DEMAND. Return one corrected question only in the required "
          "structured fields."
    )


def _realizer_user_prompt(
    context: PlanningContext,
    candidate: CandidateNextMove,
    selection: SelectionResult,
    *,
    repair_rejection_codes: Sequence[CandidateRejectionCode] = (),
) -> str:
    payload = {
        "phase_id": context.phase_id,
        "review_mode": context.review_mode.value,
        "review_objective": context.objective.to_dict(),
        "locked_move": candidate.to_dict(),
        "primary_need": selection.primary_need.value if selection.primary_need else None,
        "primary_need_source": (
            selection.primary_need_source.value if selection.primary_need_source else None
        ),
        "selector_reason_codes": [code.value for code in selection.reason_codes],
        "selected_reviewer_lens": selection.selected_reviewer_lens or context.active_reviewer_lens,
        "frozen_commit_sha": context.commit_sha,
        "frozen_evidence_package": context.evidence_package,
        "recent_questions_before_current_engine_reply": list(context.recent_questions[-8:]),
        "recent_student_turns": list(context.recent_student_turns[-8:]),
        "latest_student_turn": context.latest_student_turn,
        "latest_student_evidence_refs": list(context.latest_student_evidence_refs),
        "evidence_disputes": list(context.evidence_disputes),
        "explicit_uncertainty": list(context.explicit_uncertainty),
        "current_position": context.current_position,
        "committed_position": context.committed_position,
        "assistance_state": context.assistance_state,
        "repair_rejection_codes": [code.value for code in repair_rejection_codes],
    }
    return sanitize_model_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))[:12000]
    ).text


def _ensure_bounded_fallback_candidates(
    context: PlanningContext,
    candidates: Sequence[CandidateNextMove],
    *,
    primary_need: PlanningNeed | None,
) -> tuple[CandidateNextMove, ...]:
    """Guarantee bounded candidates for application-owned continuity needs.

    Ordinary candidate generation remains semantic. These fallbacks exist only where
    the application already knows the conversation must stay on an evidence-backed
    challenge, a direct-teaching boundary, or an active legitimate uncertainty. They
    do not invent evidence or engineering conclusions.
    """
    result = list(candidates)
    allowed = set(context.objective.required_outcomes) | set(context.objective.optional_outcomes)
    allowed_refs = allowed_evidence_refs(context)

    if primary_need is PlanningNeed.STUDENT_CHALLENGE and not any(
        candidate_addresses_need(item, PlanningNeed.STUDENT_CHALLENGE)
        and item.target_outcome in allowed
        and not (set(item.evidence_refs) - allowed_refs)
        for item in result
    ):
        challenge_target = next(
            (
                item
                for item in (
                    ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
                    ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
                    ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
                )
                if item in allowed
            ),
            None,
        )
        if challenge_target is not None:
            move_type = (
                CandidateMoveType.TEST_FINDING_SUPPORT
                if challenge_target is ObjectiveOutcome.FINDING_EVIDENCE_TESTED
                else CandidateMoveType.ADDRESS_STUDENT_CHALLENGE
            )
            refs = _safe_fallback_evidence_refs(context, allowed_refs)
            result.append(
                CandidateNextMove(
                    candidate_id="app-bounded-challenge-fallback",
                    move_type=move_type,
                    target_outcome=challenge_target,
                    evidence_refs=refs,
                    preferred_reviewer_lens=context.active_reviewer_lens or None,
                    teaching_required=False,
                    reason_codes=(SelectionReasonCode.ADDRESSES_STUDENT_CHALLENGE,),
                )
            )

    if primary_need is PlanningNeed.TEACHING_OR_TEACHBACK and not _has_selectable_teaching_candidate(
        context, result, allowed_refs
    ):
        preferred_targets = (
            ObjectiveOutcome.FOCUS_UNDERSTOOD,
            ObjectiveOutcome.FINDING_CLAIM_CLEAR,
            ObjectiveOutcome.CURRENT_POSITION_CLEAR,
            ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
            ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        )
        target = next((item for item in preferred_targets if item in allowed), None)
        if target is not None:
            result.append(
                CandidateNextMove(
                    candidate_id="app-bounded-teaching-fallback",
                    move_type=CandidateMoveType.TEACH_CONCEPT,
                    target_outcome=target,
                    evidence_refs=(),
                    preferred_reviewer_lens=context.active_reviewer_lens or None,
                    teaching_required=True,
                    reason_codes=(SelectionReasonCode.MATCHES_ASSISTANCE_LEVEL,),
                )
            )

    if primary_need is PlanningNeed.UNCERTAINTY and not any(
        candidate_addresses_need(item, PlanningNeed.UNCERTAINTY)
        and item.target_outcome in allowed
        and not (set(item.evidence_refs) - allowed_refs)
        for item in result
    ):
        uncertainty_target = next(
            (
                item
                for item in (
                    ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
                    ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
                    ObjectiveOutcome.UNCERTAINTY_CLEAR,
                )
                if item in allowed
            ),
            None,
        )
        if uncertainty_target is not None:
            result.append(
                CandidateNextMove(
                    candidate_id="app-bounded-uncertainty-fallback",
                    move_type=CandidateMoveType.SURFACE_UNCERTAINTY,
                    target_outcome=uncertainty_target,
                    evidence_refs=_safe_fallback_evidence_refs(context, allowed_refs),
                    preferred_reviewer_lens=context.active_reviewer_lens or None,
                    teaching_required=False,
                    reason_codes=(SelectionReasonCode.PRESERVES_VALID_UNCERTAINTY,),
                )
            )

    return tuple(result)


def _has_selectable_teaching_candidate(
    context: PlanningContext,
    candidates: Sequence[CandidateNextMove],
    allowed_refs: frozenset[str],
) -> bool:
    allowed = set(context.objective.required_outcomes) | set(context.objective.optional_outcomes)
    return any(
        item.move_type in {CandidateMoveType.TEACH_CONCEPT, CandidateMoveType.REQUEST_TEACH_BACK}
        and item.target_outcome in allowed
        and not (set(item.evidence_refs) - allowed_refs)
        for item in candidates
    )


def _safe_fallback_evidence_refs(
    context: PlanningContext, allowed_refs: frozenset[str]
) -> tuple[str, ...]:
    ordered = list(context.latest_student_evidence_refs) + list(context.objective_evidence_refs)
    return tuple(dict.fromkeys(ref for ref in ordered if ref in allowed_refs))[:3]


def _normalize_planner_result(
    parsed: Mapping[str, Any] | None,
) -> tuple[PlanningNeed | None, tuple[CandidateNextMove, ...]]:
    data = dict(parsed or {})
    try:
        semantic_need = PlanningNeed(str(data.get("primary_need") or ""))
    except ValueError:
        semantic_need = None

    candidates: list[CandidateNextMove] = []
    seen: set[str] = set()
    for raw in (data.get("candidates") or [])[:4]:
        if not isinstance(raw, Mapping):
            continue
        candidate_id = str(raw.get("candidate_id") or "").strip()[:80]
        if not candidate_id or candidate_id in seen:
            continue
        try:
            move_type = CandidateMoveType(str(raw.get("move_type") or ""))
            target = ObjectiveOutcome(str(raw.get("target_outcome") or ""))
        except ValueError:
            continue
        lens_value = str(raw.get("preferred_reviewer_lens") or "").strip()
        lens = lens_value if lens_value in _ALLOWED_REVIEWER_LENSES else None
        reason_codes: list[SelectionReasonCode] = []
        for value in raw.get("reason_codes") or ():
            try:
                reason_codes.append(SelectionReasonCode(str(value)))
            except ValueError:
                continue
        # A model-provided boolean does not grant teaching authority to an ordinary
        # analytical move. Only explicit teaching move types carry teaching semantics.
        teaching_required = move_type in {
            CandidateMoveType.TEACH_CONCEPT,
            CandidateMoveType.REQUEST_TEACH_BACK,
        }
        candidates.append(
            CandidateNextMove(
                candidate_id=candidate_id,
                move_type=move_type,
                target_outcome=target,
                evidence_refs=_dedupe_strings(raw.get("evidence_refs") or ()),
                preferred_reviewer_lens=lens,
                teaching_required=teaching_required,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
            )
        )
        seen.add(candidate_id)
    return semantic_need, tuple(candidates)


def _normalize_realization(parsed: Mapping[str, Any] | None) -> tuple[str, str]:
    data = dict(parsed or {})
    lead_in = sanitize_model_text(str(data.get("lead_in") or "").strip()[:1200]).text.strip()
    question = sanitize_model_text(str(data.get("question") or "").strip()[:700]).text.strip()
    return lead_in, question


def _realization_rejection_codes(
    *,
    context: PlanningContext,
    candidate: CandidateNextMove,
    lead_in: str,
    question: str,
) -> tuple[CandidateRejectionCode, ...]:
    codes: list[CandidateRejectionCode] = []
    combined = " ".join(part for part in (lead_in, question) if part).strip()
    if not question or question.count("?") != 1:
        codes.append(CandidateRejectionCode.NOT_ACTIONABLE_NOW)
    if _mentions_future_phase(combined, context.phase_id):
        codes.append(CandidateRejectionCode.FUTURE_PHASE_DEMAND)
    if question and _duplicates_prior_question(question, context.recent_questions):
        codes.append(CandidateRejectionCode.DUPLICATES_PRIOR_QUESTION)
    if _contains_unauthorized_explicit_ref(combined, allowed_evidence_refs(context)):
        codes.append(CandidateRejectionCode.NO_FROZEN_EVIDENCE_BASIS)
    if _looks_like_generic_trivia(question, candidate):
        codes.append(CandidateRejectionCode.GENERIC_TRIVIA)
    if _looks_like_artifact_theater(question, candidate):
        codes.append(CandidateRejectionCode.ARTIFACT_THEATER)
    return tuple(dict.fromkeys(codes))


def _mentions_future_phase(text: str, current_phase: str) -> bool:
    match = re.fullmatch(r"A([1-6])", str(current_phase or "").strip().upper())
    if not match:
        return False
    current = int(match.group(1))
    for value in re.findall(r"\bA([1-6])\b", str(text or "").upper()):
        if int(value) > current:
            return True
    return False


def _duplicates_prior_question(question: str, prior_questions: Sequence[str]) -> bool:
    normalized = _normalize_question(question)
    if len(normalized) < 18:
        return False
    for prior in prior_questions[-8:]:
        other = _normalize_question(prior)
        if len(other) < 18:
            continue
        if SequenceMatcher(None, normalized, other).ratio() >= 0.84:
            return True
    return False


def _contains_unauthorized_explicit_ref(text: str, allowed_refs: frozenset[str]) -> bool:
    explicit = re.findall(r"\b(?:PATH|FINDING):[^\s,;`]+", str(text or ""))
    return any(ref.rstrip(".?!:)") not in allowed_refs for ref in explicit)


def _looks_like_generic_trivia(question: str, candidate: CandidateNextMove) -> bool:
    if candidate.evidence_refs or candidate.move_type in {
        CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        CandidateMoveType.TEST_FINDING_SUPPORT,
        CandidateMoveType.ADDRESS_STUDENT_CHALLENGE,
    }:
        return False
    normalized = " ".join(str(question or "").lower().split())
    return bool(
        len(normalized) <= 100
        and re.match(r"^(what is|define|what does)\b", normalized)
        and any(word in normalized for word in ("term", "mean", "definition", "concept"))
    )


def _looks_like_artifact_theater(question: str, candidate: CandidateNextMove) -> bool:
    if candidate.move_type is CandidateMoveType.REQUEST_MISSING_EVIDENCE:
        return False
    normalized = " ".join(str(question or "").lower().split())
    return bool(
        re.search(r"\b(create|add|upload|fill out|complete)\b", normalized)
        and re.search(r"\b(file|template|document|artifact)\b", normalized)
        and not re.search(r"\bwhy|consequence|risk|evidence|verify|test|decision\b", normalized)
    )


def _extract_main_question(text: str) -> str:
    text = " ".join(str(text or "").split())
    if not text:
        return ""
    parts = re.findall(r"[^?]*\?", text)
    if parts:
        return parts[-1].strip()[:700]
    return text[:700]


def _question_similarity(left: str, right: str) -> float:
    a = _normalize_question(left)
    b = _normalize_question(right)
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 3)


def _normalize_question(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _dedupe_strings(values: Sequence[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _planner_available(ai: Any) -> bool:
    return hasattr(ai, "plan_review_turn") and ai.available()


def _realizer_available(ai: Any) -> bool:
    return hasattr(ai, "realize_review_move") and ai.available()


def _append_usage(events: list[dict[str, Any]], result: Mapping[str, Any] | None) -> None:
    usage = result.get("_usage") if isinstance(result, Mapping) else None
    if isinstance(usage, Mapping):
        events.append(dict(usage))


def _update_shadow(
    shadow: Mapping[str, Any],
    signal: Mapping[str, Any],
    *,
    status: str,
    candidate_count: int = 0,
    rejected_count: int = 0,
    same_target: bool | None = None,
    realization_failure: bool = False,
    realization_repair_attempted: bool = False,
    realization_repair_succeeded: bool = False,
) -> dict[str, Any]:
    updated = ensure_planning_shadow(shadow)
    comparison = updated["comparison"]
    if status == "completed":
        comparison["completed_plans"] += 1
    elif status == "skipped":
        comparison["skipped_plans"] += 1
    else:
        comparison["failed_plans"] += 1
    comparison["candidates_considered"] += max(0, candidate_count)
    comparison["candidates_rejected"] += max(0, rejected_count)
    if same_target is True:
        comparison["same_target_as_legacy"] += 1
    elif same_target is False:
        comparison["different_target_from_legacy"] += 1
    if realization_failure:
        comparison["realization_failures"] += 1
    if realization_repair_attempted:
        comparison["realization_repair_attempts"] += 1
    if realization_repair_succeeded:
        comparison["realization_repair_successes"] += 1
    updated["last_plan"] = dict(signal)
    return updated


def _skipped_outcome(
    shadow: Mapping[str, Any],
    *,
    reason: str,
    turn_sequence: int,
    client_turn_id: str | None,
    operation: str,
) -> PlanningShadowOutcome:
    signal = {
        "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
        "status": "skipped",
        "reason": reason,
        "turn_sequence": turn_sequence,
        "client_turn_id": client_turn_id,
        "operation": operation,
    }
    return PlanningShadowOutcome(
        signal=signal,
        shadow_state=_update_shadow(shadow, signal, status="skipped"),
    )


def _failed_outcome(
    shadow: Mapping[str, Any],
    *,
    error_type: str,
    failure_stage: str,
    turn_sequence: int,
    client_turn_id: str | None,
    operation: str,
) -> PlanningShadowOutcome:
    signal = {
        "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
        "status": "failed",
        "failure_stage": failure_stage,
        "error_type": error_type,
        "turn_sequence": turn_sequence,
        "client_turn_id": client_turn_id,
        "operation": operation,
    }
    return PlanningShadowOutcome(
        signal=signal,
        shadow_state=_update_shadow(shadow, signal, status="failed"),
    )


def _failed_after_selection(
    shadow: Mapping[str, Any],
    *,
    usage_events: Sequence[Mapping[str, Any]],
    selection: SelectionResult,
    candidates: Sequence[CandidateNextMove],
    error_type: str,
    failure_stage: str,
    turn_sequence: int,
    client_turn_id: str | None,
    operation: str,
    realization_repair_attempted: bool = False,
    initial_realization_rejections: Sequence[CandidateRejectionCode] = (),
) -> PlanningShadowOutcome:
    signal = {
        "schema_version": PLANNING_SHADOW_SCHEMA_VERSION,
        "status": "failed",
        "failure_stage": failure_stage,
        "error_type": error_type,
        "turn_sequence": turn_sequence,
        "client_turn_id": client_turn_id,
        "operation": operation,
        "primary_need": selection.primary_need.value if selection.primary_need else None,
        "primary_need_source": (
            selection.primary_need_source.value if selection.primary_need_source else None
        ),
        "candidate_count": len(candidates),
        "candidate_moves": [item.to_dict() for item in candidates],
        "selected_candidate_id": selection.selected_candidate_id,
        "selected_move_type": selection.selected_move_type.value,
        "target_outcome": selection.target_outcome.value,
        "realization_repair": {
            "attempted": realization_repair_attempted,
            "succeeded": False,
            "initial_rejection_codes": [
                code.value for code in initial_realization_rejections
            ],
            "final_rejection_codes": [],
        },
    }
    return PlanningShadowOutcome(
        signal=signal,
        shadow_state=_update_shadow(
            shadow,
            signal,
            status="failed",
            candidate_count=len(candidates),
            rejected_count=len(selection.rejected_candidates),
            realization_failure=True,
            realization_repair_attempted=realization_repair_attempted,
        ),
        usage_events=tuple(dict(event) for event in usage_events),
    )
