from __future__ import annotations

from typing import Any, Mapping, Sequence

from .reasoning_validation import ReasoningStatus
from .review_planning import (
    CandidateMoveType,
    CandidateNextMove,
    CandidateRejection,
    CandidateRejectionCode,
    ObjectiveOutcome,
    PlanningContext,
    SelectionReasonCode,
    SelectionResult,
)


# A candidate must target an outcome that belongs to the locked Review Objective
# and is semantically compatible with the proposed engineering move. This keeps
# the model from using a valid enum to smuggle in an unrelated planning action.
_MOVE_TARGETS: dict[CandidateMoveType, frozenset[ObjectiveOutcome]] = {
    CandidateMoveType.CLARIFY_CONSEQUENCE: frozenset(
        {
            ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
            ObjectiveOutcome.IMPORTANT_IMPLICATION_CLEAR,
            ObjectiveOutcome.FINDING_ENGINEERING_IMPLICATION_CLEAR,
        }
    ),
    CandidateMoveType.TEST_EVIDENCE_BOUNDARY: frozenset(
        {
            ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
            ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
            ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
        }
    ),
    CandidateMoveType.MAKE_POSITION_EXPLICIT: frozenset(
        {
            ObjectiveOutcome.CURRENT_POSITION_CLEAR,
            ObjectiveOutcome.FOCUS_UNDERSTOOD,
            ObjectiveOutcome.FINDING_CLAIM_CLEAR,
        }
    ),
    CandidateMoveType.CLARIFY_ACTION_BOUNDARY: frozenset(
        {
            ObjectiveOutcome.ACTION_BOUNDARY_CLEAR,
            ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
            ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
        }
    ),
    CandidateMoveType.ESTABLISH_OWNERSHIP: frozenset({ObjectiveOutcome.OWNERSHIP_CLEAR}),
    CandidateMoveType.ESTABLISH_CHANGE_TRIGGER: frozenset(
        {
            ObjectiveOutcome.CHANGE_OR_CLOSURE_CONDITION_CLEAR,
            ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
            ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
        }
    ),
    CandidateMoveType.SURFACE_UNCERTAINTY: frozenset(
        {
            ObjectiveOutcome.UNCERTAINTY_CLEAR,
            ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
            ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
        }
    ),
    CandidateMoveType.TEST_TRADEOFF: frozenset({ObjectiveOutcome.TRADEOFF_CLEAR}),
    CandidateMoveType.TEST_FINDING_SUPPORT: frozenset(
        {ObjectiveOutcome.FINDING_CLAIM_CLEAR, ObjectiveOutcome.FINDING_EVIDENCE_TESTED}
    ),
    CandidateMoveType.RECONCILE_CONTRADICTION: frozenset(
        {
            ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
            ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
            ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
            ObjectiveOutcome.CURRENT_POSITION_CLEAR,
        }
    ),
    CandidateMoveType.ADDRESS_STUDENT_CHALLENGE: frozenset(
        {
            ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
            ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
            ObjectiveOutcome.FINDING_CLAIM_CLEAR,
            ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
        }
    ),
    CandidateMoveType.REQUEST_MISSING_EVIDENCE: frozenset(
        {
            ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
            ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
            ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
            ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
            ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
            ObjectiveOutcome.UNCERTAINTY_CLEAR,
        }
    ),
    CandidateMoveType.TEACH_CONCEPT: frozenset(ObjectiveOutcome),
    CandidateMoveType.REQUEST_TEACH_BACK: frozenset(ObjectiveOutcome),
    CandidateMoveType.STRESS_TEST_POSITION: frozenset(
        {
            ObjectiveOutcome.CURRENT_POSITION_CLEAR,
            ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
            ObjectiveOutcome.IMPORTANT_IMPLICATION_CLEAR,
            ObjectiveOutcome.FINDING_ENGINEERING_IMPLICATION_CLEAR,
            ObjectiveOutcome.TRADEOFF_CLEAR,
        }
    ),
    CandidateMoveType.SYNTHESIZE_OBJECTIVE: frozenset(ObjectiveOutcome),
    CandidateMoveType.CLOSE_WITH_UNRESOLVED_EVIDENCE: frozenset(
        {
            ObjectiveOutcome.UNCERTAINTY_CLEAR,
            ObjectiveOutcome.CHANGE_OR_CLOSURE_CONDITION_CLEAR,
            ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
            ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
        }
    ),
    CandidateMoveType.HANDOFF_EXPERTISE: frozenset(ObjectiveOutcome),
}

# The current reasoning validator still validates the original eight reasoning
# dimensions. This partial mapping lets the selector avoid re-targeting an
# outcome that is already independently established without pretending those
# dimensions fully define Focused/Finding Review completion.
_OUTCOME_REASONING_DIMENSION: dict[ObjectiveOutcome, str] = {
    ObjectiveOutcome.CURRENT_POSITION_CLEAR: "decision_explicit",
    ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR: "evidence_boundary_visible",
    ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR: "consequence_visible",
    ObjectiveOutcome.ACTION_BOUNDARY_CLEAR: "boundary_visible",
    ObjectiveOutcome.OWNERSHIP_CLEAR: "ownership_visible",
    ObjectiveOutcome.CHANGE_OR_CLOSURE_CONDITION_CLEAR: "change_trigger_visible",
    ObjectiveOutcome.UNCERTAINTY_CLEAR: "uncertainty_visible",
    ObjectiveOutcome.TRADEOFF_CLEAR: "tradeoff_visible",
    ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED: "evidence_boundary_visible",
    ObjectiveOutcome.IMPORTANT_IMPLICATION_CLEAR: "consequence_visible",
    ObjectiveOutcome.FINDING_EVIDENCE_TESTED: "evidence_boundary_visible",
    ObjectiveOutcome.FINDING_ENGINEERING_IMPLICATION_CLEAR: "consequence_visible",
}

_ASSISTANCE_INTENTS = frozenset(
    {"stuck", "answer_seeking", "frustration", "misconception", "simplify_request"}
)
_CHALLENGE_INTENTS = frozenset(
    {"disagreement", "evidence_dispute", "self_correction", "meta_misunderstood"}
)
_CLOSURE_MOVES = frozenset(
    {CandidateMoveType.SYNTHESIZE_OBJECTIVE, CandidateMoveType.CLOSE_WITH_UNRESOLVED_EVIDENCE}
)


def reasoning_dimension_for_outcome(outcome: ObjectiveOutcome) -> str | None:
    """Return the legacy reasoning dimension most closely aligned to an objective outcome."""
    return _OUTCOME_REASONING_DIMENSION.get(outcome)


class NextQuestionSelector:
    """Application-owned selector for semantic planner candidates.

    Selection is deterministic after the model proposes a bounded candidate set.
    Hard authority constraints run before ranking. No model can bypass these
    objective, evidence, assistance, or validated-state checks.
    """

    def select(
        self,
        *,
        context: PlanningContext,
        candidates: Sequence[CandidateNextMove],
    ) -> tuple[SelectionResult | None, tuple[CandidateRejection, ...]]:
        allowed_outcomes = set(context.objective.required_outcomes) | set(context.objective.optional_outcomes)
        allowed_refs = allowed_evidence_refs(context)
        rejected: list[CandidateRejection] = []
        selectable: list[tuple[int, int, CandidateNextMove, tuple[SelectionReasonCode, ...]]] = []
        assistance_needed = context_requires_teaching(context)

        for index, candidate in enumerate(candidates):
            rejection_codes: list[CandidateRejectionCode] = []
            if candidate.target_outcome not in allowed_outcomes:
                rejection_codes.append(CandidateRejectionCode.OUTSIDE_REVIEW_OBJECTIVE)
            if candidate.target_outcome not in _MOVE_TARGETS.get(candidate.move_type, frozenset()):
                rejection_codes.append(CandidateRejectionCode.OUTSIDE_REVIEW_OBJECTIVE)
            if any(ref not in allowed_refs for ref in candidate.evidence_refs):
                rejection_codes.append(CandidateRejectionCode.NO_FROZEN_EVIDENCE_BASIS)
            if (
                _outcome_status(context, candidate.target_outcome) == ReasoningStatus.VALIDATED.value
                and not _can_deepen_validated_outcome(candidate)
            ):
                rejection_codes.append(CandidateRejectionCode.ALREADY_ESTABLISHED)
            if assistance_needed and not _is_teaching_move(candidate):
                rejection_codes.append(CandidateRejectionCode.TEACHING_REQUIRED_FIRST)
            if candidate.move_type in _CLOSURE_MOVES and not _closure_move_allowed(context, candidate):
                rejection_codes.append(CandidateRejectionCode.CONFLICTS_WITH_LOCKED_PURPOSE)

            if rejection_codes:
                rejected.append(
                    CandidateRejection(
                        candidate_id=candidate.candidate_id,
                        rejection_codes=tuple(dict.fromkeys(rejection_codes)),
                    )
                )
                continue

            score, reasons = _score_candidate(context, candidate)
            selectable.append((score, -index, candidate, reasons))

        if not selectable:
            return None, tuple(rejected)

        selectable.sort(key=lambda item: (item[0], item[1]), reverse=True)
        _, _, selected, reasons = selectable[0]
        for _, _, candidate, _ in selectable[1:]:
            rejected.append(
                CandidateRejection(
                    candidate_id=candidate.candidate_id,
                    rejection_codes=(CandidateRejectionCode.LOWER_VALUE_THAN_SELECTED,),
                )
            )

        result = SelectionResult(
            selected_candidate_id=selected.candidate_id,
            selected_move_type=selected.move_type,
            target_outcome=selected.target_outcome,
            selected_reviewer_lens=selected.preferred_reviewer_lens,
            teaching_required=selected.teaching_required,
            reason_codes=reasons,
            rejected_candidates=tuple(rejected),
        )
        return result, tuple(rejected)


def allowed_evidence_refs(context: PlanningContext) -> frozenset[str]:
    refs: set[str] = set(context.objective_evidence_refs)
    refs.update(context.latest_student_evidence_refs)
    refs.update(_dedupe_strings(context.current_challenge.get("evidence_refs") or ()))
    package = dict(context.evidence_package or {})

    for item in package.get("relevant_items") or ():
        if not isinstance(item, Mapping):
            continue
        if item.get("ref"):
            refs.add(str(item["ref"]))
        title = str(item.get("title") or "").strip()
        if title:
            refs.add(f"PATH:{title}")
        equivalent = str(item.get("equivalent_path") or "").strip()
        if equivalent:
            refs.add(f"PATH:{equivalent}")

    for artifact in package.get("relevant_artifacts") or ():
        if isinstance(artifact, Mapping) and str(artifact.get("path") or "").strip():
            refs.add(f"PATH:{str(artifact['path']).strip()}")

    finding = (package.get("challenge") or {}).get("finding")
    if isinstance(finding, Mapping):
        finding_id = str(finding.get("id") or "").strip()
        if finding_id:
            refs.add(f"FINDING:{finding_id}")
        refs.update(_dedupe_strings(finding.get("evidence_refs") or ()))

    for finding in context.current_findings:
        finding_id = str(finding.get("id") or "").strip()
        if finding_id:
            refs.add(f"FINDING:{finding_id}")
        refs.update(_dedupe_strings(finding.get("evidence_refs") or ()))

    return frozenset(refs)


def _score_candidate(
    context: PlanningContext,
    candidate: CandidateNextMove,
) -> tuple[int, tuple[SelectionReasonCode, ...]]:
    score = 0
    reasons: list[SelectionReasonCode] = [
        SelectionReasonCode.ADVANCES_OBJECTIVE,
        SelectionReasonCode.PHASE_APPROPRIATE,
        SelectionReasonCode.NOVEL_VS_PRIOR_QUESTIONS,
    ]
    required = candidate.target_outcome in set(context.objective.required_outcomes)
    status = _outcome_status(context, candidate.target_outcome)
    if required:
        score += 55
        reasons.append(SelectionReasonCode.TARGETS_REQUIRED_UNRESOLVED_OUTCOME)
    else:
        score += 12
    if status == ReasoningStatus.UNESTABLISHED.value:
        score += 30
    elif status == ReasoningStatus.PARTIAL.value:
        score += 22

    if candidate.evidence_refs:
        score += 16
        reasons.append(SelectionReasonCode.EVIDENCE_GROUNDED)
    elif candidate.move_type is CandidateMoveType.REQUEST_MISSING_EVIDENCE:
        score += 18
        reasons.append(SelectionReasonCode.EVIDENCE_GAP_IS_THE_OBJECT)
    elif candidate.move_type is CandidateMoveType.TEST_EVIDENCE_BOUNDARY:
        # Testing an evidence boundary is itself an analytical action even when
        # the planner does not attach a specific path. Do not let a generic
        # consequence probe win merely because the model omitted an otherwise
        # optional candidate evidence reference.
        score += 10
        reasons.append(SelectionReasonCode.EVIDENCE_GAP_IS_THE_OBJECT)

    if set(candidate.evidence_refs) & set(context.latest_student_evidence_refs):
        score += 10
        reasons.append(SelectionReasonCode.CONTINUES_STUDENT_REASONING)

    # Consequence is important, but it is not a universal tie-breaker. In the
    # replicated PR4D baseline, the old unconditional consequence bonus caused
    # the selector to re-ask implications after students had already surfaced
    # a more immediate evidence, contradiction, uncertainty, or understanding
    # defect. Keep the reason code for observability without adding rank weight.
    if candidate.target_outcome in {
        ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
        ObjectiveOutcome.IMPORTANT_IMPLICATION_CLEAR,
        ObjectiveOutcome.FINDING_ENGINEERING_IMPLICATION_CLEAR,
    }:
        reasons.append(SelectionReasonCode.HIGH_ENGINEERING_CONSEQUENCE)

    if context_requires_teaching(context) and _is_teaching_move(candidate):
        score += 60
        reasons.append(SelectionReasonCode.MATCHES_ASSISTANCE_LEVEL)
    elif candidate.teaching_required and _is_teaching_move(candidate):
        # The semantic planner can independently recognize a teach-back need
        # from the student's words even when the upstream intent classifier did
        # not. Give that bounded signal meaningful but non-authoritative weight.
        score += 30
        reasons.append(SelectionReasonCode.MATCHES_ASSISTANCE_LEVEL)
    elif not candidate.teaching_required:
        score += 5
        reasons.append(SelectionReasonCode.MATCHES_ASSISTANCE_LEVEL)

    intent = str(context.assistance_state.get("interpreted_intent") or "").lower()
    if intent in _CHALLENGE_INTENTS and candidate.move_type in {
        CandidateMoveType.ADDRESS_STUDENT_CHALLENGE,
        CandidateMoveType.RECONCILE_CONTRADICTION,
        CandidateMoveType.TEST_FINDING_SUPPORT,
    }:
        score += 55
        reasons.append(SelectionReasonCode.ADDRESSES_STUDENT_CHALLENGE)
        if context.evidence_disputes or any(
            str(item.get("status") or "") in {"corrected", "evidence_disputed"}
            for item in context.finding_states
        ):
            reasons.append(SelectionReasonCode.REVIEWER_CORRECTION_REQUIRED)

    if _has_active_uncertainty(context) and candidate.move_type in {
        CandidateMoveType.SURFACE_UNCERTAINTY,
        CandidateMoveType.REQUEST_MISSING_EVIDENCE,
        CandidateMoveType.ESTABLISH_CHANGE_TRIGGER,
        CandidateMoveType.CLOSE_WITH_UNRESOLVED_EVIDENCE,
    }:
        score += 50
        reasons.append(SelectionReasonCode.PRESERVES_VALID_UNCERTAINTY)

    if intent == "self_correction" and candidate.move_type in {
        CandidateMoveType.CLARIFY_ACTION_BOUNDARY,
        CandidateMoveType.ESTABLISH_CHANGE_TRIGGER,
    }:
        score += 30
        reasons.append(SelectionReasonCode.CONTINUES_STUDENT_REASONING)

    # Small tie-breakers express conversational value, not a hidden universal
    # checklist. They matter only after objective/validation/context scoring.
    if candidate.move_type is CandidateMoveType.MAKE_POSITION_EXPLICIT:
        score += 6
    elif candidate.move_type in {
        CandidateMoveType.CLARIFY_ACTION_BOUNDARY,
        CandidateMoveType.ESTABLISH_CHANGE_TRIGGER,
    }:
        score += 8
    elif candidate.move_type is CandidateMoveType.ESTABLISH_OWNERSHIP:
        score += 4

    if candidate.move_type in _CLOSURE_MOVES:
        score += 5
        reasons.append(SelectionReasonCode.SUPPORTS_OBJECTIVE_CLOSURE)
    if candidate.move_type in {
        CandidateMoveType.SURFACE_UNCERTAINTY,
        CandidateMoveType.CLOSE_WITH_UNRESOLVED_EVIDENCE,
    }:
        reasons.append(SelectionReasonCode.PRESERVES_VALID_UNCERTAINTY)

    return score, tuple(dict.fromkeys(reasons))


def _outcome_status(context: PlanningContext, outcome: ObjectiveOutcome) -> str:
    dimension = _OUTCOME_REASONING_DIMENSION.get(outcome)
    if not dimension:
        return ReasoningStatus.UNESTABLISHED.value
    shadow = context.validated_reasoning_state or {}
    dimensions = shadow.get("dimensions") if isinstance(shadow, Mapping) else {}
    current = (dimensions or {}).get(dimension) if isinstance(dimensions, Mapping) else None
    if not isinstance(current, Mapping):
        return ReasoningStatus.UNESTABLISHED.value
    status = str(current.get("status") or ReasoningStatus.UNESTABLISHED.value)
    if status not in {item.value for item in ReasoningStatus}:
        return ReasoningStatus.UNESTABLISHED.value
    return status


def context_requires_teaching(context: PlanningContext) -> bool:
    """Return whether ordinary challenge moves must yield to bounded teaching."""
    intent = str(context.assistance_state.get("interpreted_intent") or "").lower()
    return intent in _ASSISTANCE_INTENTS or bool(context.assistance_state.get("teaching_needed"))


def _has_active_uncertainty(context: PlanningContext) -> bool:
    if context.explicit_uncertainty:
        return True
    return _outcome_status(context, ObjectiveOutcome.UNCERTAINTY_CLEAR) in {
        ReasoningStatus.PARTIAL.value,
        ReasoningStatus.VALIDATED.value,
    }


def _can_deepen_validated_outcome(candidate: CandidateNextMove) -> bool:
    """Allow a move that tests/deepens reasoning without merely re-asking it."""
    return candidate.move_type in {
        CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        CandidateMoveType.REQUEST_MISSING_EVIDENCE,
        CandidateMoveType.RECONCILE_CONTRADICTION,
        CandidateMoveType.ADDRESS_STUDENT_CHALLENGE,
        CandidateMoveType.TEST_FINDING_SUPPORT,
        CandidateMoveType.STRESS_TEST_POSITION,
        CandidateMoveType.TEACH_CONCEPT,
        CandidateMoveType.REQUEST_TEACH_BACK,
    }


def _is_teaching_move(candidate: CandidateNextMove) -> bool:
    return candidate.teaching_required or candidate.move_type in {
        CandidateMoveType.TEACH_CONCEPT,
        CandidateMoveType.REQUEST_TEACH_BACK,
    }


def _closure_move_allowed(context: PlanningContext, candidate: CandidateNextMove) -> bool:
    if candidate.move_type is CandidateMoveType.CLOSE_WITH_UNRESOLVED_EVIDENCE:
        uncertainty = _outcome_status(context, ObjectiveOutcome.UNCERTAINTY_CLEAR)
        return bool(context.explicit_uncertainty or context.evidence_disputes) and uncertainty in {
            ReasoningStatus.PARTIAL.value,
            ReasoningStatus.VALIDATED.value,
        }

    # Synthesis is allowed only when every required outcome that the current
    # independent validator can evaluate is already validated. Unmapped Focused
    # or Finding outcomes remain outside PR3's completion authority.
    mapped = [
        outcome for outcome in context.objective.required_outcomes if outcome in _OUTCOME_REASONING_DIMENSION
    ]
    return bool(mapped) and all(
        _outcome_status(context, outcome) == ReasoningStatus.VALIDATED.value for outcome in mapped
    )


def _dedupe_strings(values: Sequence[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)
