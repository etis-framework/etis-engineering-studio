from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import uuid4


REVIEW_CONTROL_SCHEMA_VERSION = 1
REVIEW_OBJECTIVE_SCHEMA_VERSION = 1


class ReviewMode(str, Enum):
    BOARD_REVIEW = "board_review"
    FOCUSED_REVIEW = "focused_review"
    FINDING_REVIEW = "finding_review"


class ReviewObjectiveKind(str, Enum):
    BOARD_POSITION = "board_position"
    FOCUSED_ASSESSMENT = "focused_assessment"
    FINDING_ANALYSIS = "finding_analysis"


class ReasoningValidationMode(str, Enum):
    LEGACY = "legacy"
    SHADOW = "shadow"
    VALIDATED = "validated"


class ReviewPlanningMode(str, Enum):
    LEGACY = "legacy"
    SHADOW = "shadow"
    SELECTED = "selected"


class ObjectiveOutcome(str, Enum):
    CURRENT_POSITION_CLEAR = "CURRENT_POSITION_CLEAR"
    EVIDENCE_BOUNDARY_CLEAR = "EVIDENCE_BOUNDARY_CLEAR"
    ENGINEERING_CONSEQUENCE_CLEAR = "ENGINEERING_CONSEQUENCE_CLEAR"
    ACTION_BOUNDARY_CLEAR = "ACTION_BOUNDARY_CLEAR"
    OWNERSHIP_CLEAR = "OWNERSHIP_CLEAR"
    CHANGE_OR_CLOSURE_CONDITION_CLEAR = "CHANGE_OR_CLOSURE_CONDITION_CLEAR"
    UNCERTAINTY_CLEAR = "UNCERTAINTY_CLEAR"
    TRADEOFF_CLEAR = "TRADEOFF_CLEAR"
    FOCUS_UNDERSTOOD = "FOCUS_UNDERSTOOD"
    CURRENT_EVIDENCE_ASSESSED = "CURRENT_EVIDENCE_ASSESSED"
    IMPORTANT_IMPLICATION_CLEAR = "IMPORTANT_IMPLICATION_CLEAR"
    NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR = "NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR"
    FINDING_CLAIM_CLEAR = "FINDING_CLAIM_CLEAR"
    FINDING_EVIDENCE_TESTED = "FINDING_EVIDENCE_TESTED"
    FINDING_ENGINEERING_IMPLICATION_CLEAR = "FINDING_ENGINEERING_IMPLICATION_CLEAR"
    NEXT_ACTION_OR_UNCERTAINTY_CLEAR = "NEXT_ACTION_OR_UNCERTAINTY_CLEAR"


class ObjectiveConclusion(str, Enum):
    DEFENSIBLE_POSITION = "DEFENSIBLE_POSITION"
    EVIDENCE_BOUNDED_ASSESSMENT = "EVIDENCE_BOUNDED_ASSESSMENT"
    NEXT_IMPROVEMENT_IDENTIFIED = "NEXT_IMPROVEMENT_IDENTIFIED"
    FINDING_SUPPORTED = "FINDING_SUPPORTED"
    FINDING_CREDIBLY_CHALLENGED = "FINDING_CREDIBLY_CHALLENGED"
    CORRECTION_RECOMMENDED = "CORRECTION_RECOMMENDED"
    RISK_RESPONSE_BOUNDED = "RISK_RESPONSE_BOUNDED"
    DEFER_WITH_RATIONALE = "DEFER_WITH_RATIONALE"
    ADDITIONAL_EVIDENCE_REQUIRED = "ADDITIONAL_EVIDENCE_REQUIRED"
    UNRESOLVED_WITH_REASON = "UNRESOLVED_WITH_REASON"


class SubjectType(str, Enum):
    CHALLENGE = "challenge"
    FOCUS = "focus"
    FINDING = "finding"


class CandidateMoveType(str, Enum):
    CLARIFY_CONSEQUENCE = "CLARIFY_CONSEQUENCE"
    TEST_EVIDENCE_BOUNDARY = "TEST_EVIDENCE_BOUNDARY"
    MAKE_POSITION_EXPLICIT = "MAKE_POSITION_EXPLICIT"
    CLARIFY_ACTION_BOUNDARY = "CLARIFY_ACTION_BOUNDARY"
    ESTABLISH_OWNERSHIP = "ESTABLISH_OWNERSHIP"
    ESTABLISH_CHANGE_TRIGGER = "ESTABLISH_CHANGE_TRIGGER"
    SURFACE_UNCERTAINTY = "SURFACE_UNCERTAINTY"
    TEST_TRADEOFF = "TEST_TRADEOFF"
    TEST_FINDING_SUPPORT = "TEST_FINDING_SUPPORT"
    RECONCILE_CONTRADICTION = "RECONCILE_CONTRADICTION"
    ADDRESS_STUDENT_CHALLENGE = "ADDRESS_STUDENT_CHALLENGE"
    REQUEST_MISSING_EVIDENCE = "REQUEST_MISSING_EVIDENCE"
    TEACH_CONCEPT = "TEACH_CONCEPT"
    REQUEST_TEACH_BACK = "REQUEST_TEACH_BACK"
    STRESS_TEST_POSITION = "STRESS_TEST_POSITION"
    SYNTHESIZE_OBJECTIVE = "SYNTHESIZE_OBJECTIVE"
    CLOSE_WITH_UNRESOLVED_EVIDENCE = "CLOSE_WITH_UNRESOLVED_EVIDENCE"
    HANDOFF_EXPERTISE = "HANDOFF_EXPERTISE"


class SelectionReasonCode(str, Enum):
    ADVANCES_OBJECTIVE = "ADVANCES_OBJECTIVE"
    TARGETS_REQUIRED_UNRESOLVED_OUTCOME = "TARGETS_REQUIRED_UNRESOLVED_OUTCOME"
    EVIDENCE_GROUNDED = "EVIDENCE_GROUNDED"
    EVIDENCE_GAP_IS_THE_OBJECT = "EVIDENCE_GAP_IS_THE_OBJECT"
    HIGH_ENGINEERING_CONSEQUENCE = "HIGH_ENGINEERING_CONSEQUENCE"
    CONTINUES_STUDENT_REASONING = "CONTINUES_STUDENT_REASONING"
    NOVEL_VS_PRIOR_QUESTIONS = "NOVEL_VS_PRIOR_QUESTIONS"
    PHASE_APPROPRIATE = "PHASE_APPROPRIATE"
    MATCHES_ASSISTANCE_LEVEL = "MATCHES_ASSISTANCE_LEVEL"
    ADDRESSES_STUDENT_CHALLENGE = "ADDRESSES_STUDENT_CHALLENGE"
    REVIEWER_CORRECTION_REQUIRED = "REVIEWER_CORRECTION_REQUIRED"
    SUPPORTS_OBJECTIVE_CLOSURE = "SUPPORTS_OBJECTIVE_CLOSURE"
    PRESERVES_VALID_UNCERTAINTY = "PRESERVES_VALID_UNCERTAINTY"


class CandidateRejectionCode(str, Enum):
    OUTSIDE_REVIEW_OBJECTIVE = "OUTSIDE_REVIEW_OBJECTIVE"
    CONFLICTS_WITH_LOCKED_PURPOSE = "CONFLICTS_WITH_LOCKED_PURPOSE"
    FUTURE_PHASE_DEMAND = "FUTURE_PHASE_DEMAND"
    NO_FROZEN_EVIDENCE_BASIS = "NO_FROZEN_EVIDENCE_BASIS"
    DUPLICATES_PRIOR_QUESTION = "DUPLICATES_PRIOR_QUESTION"
    ALREADY_ESTABLISHED = "ALREADY_ESTABLISHED"
    GENERIC_TRIVIA = "GENERIC_TRIVIA"
    ARTIFACT_THEATER = "ARTIFACT_THEATER"
    IGNORES_STUDENT_CORRECTION = "IGNORES_STUDENT_CORRECTION"
    ASSUMES_REVIEWER_IS_CORRECT = "ASSUMES_REVIEWER_IS_CORRECT"
    TEACHING_REQUIRED_FIRST = "TEACHING_REQUIRED_FIRST"
    TOO_BROAD = "TOO_BROAD"
    NOT_ACTIONABLE_NOW = "NOT_ACTIONABLE_NOW"
    LOWER_VALUE_THAN_SELECTED = "LOWER_VALUE_THAN_SELECTED"


@dataclass(frozen=True)
class ObjectiveSubject:
    subject_type: SubjectType
    source_id: str
    title: str
    statement: str
    related_finding_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(frozen=True)
class ReviewObjective:
    schema_version: int
    objective_id: str
    objective_kind: ReviewObjectiveKind
    review_mode: ReviewMode
    phase_id: str
    purpose: str
    subject: ObjectiveSubject
    evidence_refs: tuple[str, ...]
    required_outcomes: tuple[ObjectiveOutcome, ...]
    optional_outcomes: tuple[ObjectiveOutcome, ...]
    permitted_conclusions: tuple[ObjectiveConclusion, ...]
    allows_unresolved: bool
    derivation_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(frozen=True)
class PlanningContext:
    session_id: int | None
    phase_id: str
    review_mode: ReviewMode
    reasoning_mode: ReasoningValidationMode
    planning_mode: ReviewPlanningMode
    objective: ReviewObjective
    snapshot_id: int | None
    commit_sha: str
    evidence_package: Mapping[str, Any]
    objective_evidence_refs: tuple[str, ...]
    current_challenge: Mapping[str, Any]
    current_findings: tuple[Mapping[str, Any], ...] = ()
    finding_states: tuple[Mapping[str, Any], ...] = ()
    focus: str = ""
    legacy_reasoning_state: Mapping[str, bool] = field(default_factory=dict)
    validated_reasoning_state: Mapping[str, Any] | None = None
    reasoning_authority: str = "legacy_semantic_derived"
    recent_questions: tuple[str, ...] = ()
    recent_student_turns: tuple[str, ...] = ()
    latest_student_turn: str = ""
    latest_student_evidence_refs: tuple[str, ...] = ()
    conversation_memory: Mapping[str, Any] = field(default_factory=dict)
    reviewer_corrections: tuple[Mapping[str, Any], ...] = ()
    evidence_disputes: tuple[Mapping[str, Any], ...] = ()
    explicit_uncertainty: tuple[str, ...] = ()
    current_position: str = ""
    committed_position: Mapping[str, Any] | None = None
    coaching_level: int = 1
    assistance_state: Mapping[str, Any] = field(default_factory=dict)
    active_reviewer_lens: str = ""


@dataclass(frozen=True)
class CandidateNextMove:
    candidate_id: str
    move_type: CandidateMoveType
    target_outcome: ObjectiveOutcome
    evidence_refs: tuple[str, ...] = ()
    preferred_reviewer_lens: str | None = None
    teaching_required: bool = False
    reason_codes: tuple[SelectionReasonCode, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(frozen=True)
class CandidateRejection:
    candidate_id: str
    rejection_codes: tuple[CandidateRejectionCode, ...]

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(frozen=True)
class SelectionResult:
    selected_candidate_id: str
    selected_move_type: CandidateMoveType
    target_outcome: ObjectiveOutcome
    selected_reviewer_lens: str | None = None
    teaching_required: bool = False
    reason_codes: tuple[SelectionReasonCode, ...] = ()
    rejected_candidates: tuple[CandidateRejection, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


def canonical_review_mode(raw_mode: str | None) -> ReviewMode:
    if (raw_mode or "").strip().lower() == ReviewMode.FOCUSED_REVIEW.value:
        return ReviewMode.FOCUSED_REVIEW
    if (raw_mode or "").strip().lower() == ReviewMode.FINDING_REVIEW.value:
        return ReviewMode.FINDING_REVIEW
    return ReviewMode.BOARD_REVIEW


def build_review_objective(
    *,
    raw_mode: str | None,
    phase_id: str,
    challenge: Any,
    focus: str | None = None,
    related_finding_ids: Sequence[str] | None = None,
    entry_intent: str = "review",
    objective_id: str | None = None,
) -> ReviewObjective:
    mode = canonical_review_mode(raw_mode)
    challenge_id = str(_value(challenge, "id", "review-challenge"))
    challenge_title = str(_value(challenge, "title", "Engineering Review"))
    challenge_statement = str(
        _value(challenge, "noticed", "")
        or _value(challenge, "prompt", "")
        or challenge_title
    )
    evidence_refs = _dedupe_strings(_value(challenge, "evidence_refs", ()) or ())

    if mode is ReviewMode.FOCUSED_REVIEW:
        focus_text = (focus or "").strip()
        derivation_codes = ["FOCUSED_REVIEW_STUDENT_CONCERN"]
        if focus_text:
            subject = ObjectiveSubject(
                subject_type=SubjectType.FOCUS,
                source_id="student-focus",
                title=focus_text[:160],
                statement=focus_text,
            )
        else:
            derivation_codes = ["FOCUS_MISSING_FALLBACK_CHALLENGE"]
            subject = ObjectiveSubject(
                subject_type=SubjectType.CHALLENGE,
                source_id=challenge_id,
                title=challenge_title,
                statement=challenge_statement,
            )
        return ReviewObjective(
            schema_version=REVIEW_OBJECTIVE_SCHEMA_VERSION,
            objective_id=objective_id or str(uuid4()),
            objective_kind=ReviewObjectiveKind.FOCUSED_ASSESSMENT,
            review_mode=mode,
            phase_id=phase_id,
            purpose=(
                "Develop the strongest evidence-bounded assessment presently possible "
                "for the student's chosen concern, identify its important engineering "
                "implication, and determine the most useful improvement or evidence need."
            ),
            subject=subject,
            evidence_refs=evidence_refs,
            required_outcomes=(
                ObjectiveOutcome.FOCUS_UNDERSTOOD,
                ObjectiveOutcome.CURRENT_EVIDENCE_ASSESSED,
                ObjectiveOutcome.IMPORTANT_IMPLICATION_CLEAR,
                ObjectiveOutcome.NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR,
            ),
            optional_outcomes=(
                ObjectiveOutcome.UNCERTAINTY_CLEAR,
                ObjectiveOutcome.TRADEOFF_CLEAR,
                ObjectiveOutcome.OWNERSHIP_CLEAR,
            ),
            permitted_conclusions=(
                ObjectiveConclusion.EVIDENCE_BOUNDED_ASSESSMENT,
                ObjectiveConclusion.NEXT_IMPROVEMENT_IDENTIFIED,
                ObjectiveConclusion.ADDITIONAL_EVIDENCE_REQUIRED,
                ObjectiveConclusion.UNRESOLVED_WITH_REASON,
            ),
            allows_unresolved=True,
            derivation_codes=tuple(derivation_codes),
        )

    if mode is ReviewMode.FINDING_REVIEW:
        selected_ids = _dedupe_strings(related_finding_ids or ())
        finding = _value(challenge, "finding", None) or {}
        finding_id = str(_value(finding, "id", challenge_id))
        finding_title = str(_value(finding, "title", challenge_title))
        finding_statement = str(
            _value(finding, "statement", "")
            or challenge_statement
            or finding_title
        )
        intent_code = _entry_intent_code(entry_intent)

        if not selected_ids or finding_id not in selected_ids:
            return ReviewObjective(
                schema_version=REVIEW_OBJECTIVE_SCHEMA_VERSION,
                objective_id=objective_id or str(uuid4()),
                objective_kind=ReviewObjectiveKind.FINDING_ANALYSIS,
                review_mode=mode,
                phase_id=phase_id,
                purpose=(
                    "Preserve the legacy review challenge when Finding Review was requested "
                    "without a valid selected finding, while marking the malformed selection "
                    "for later compatibility handling."
                ),
                subject=ObjectiveSubject(
                    subject_type=SubjectType.CHALLENGE,
                    source_id=challenge_id,
                    title=challenge_title,
                    statement=challenge_statement,
                ),
                evidence_refs=evidence_refs,
                required_outcomes=(),
                optional_outcomes=(),
                permitted_conclusions=(ObjectiveConclusion.UNRESOLVED_WITH_REASON,),
                allows_unresolved=True,
                derivation_codes=(
                    "FINDING_SELECTION_MISSING_FALLBACK_CHALLENGE",
                    intent_code,
                ),
            )

        related_ids = tuple(x for x in selected_ids if x != finding_id)
        return ReviewObjective(
            schema_version=REVIEW_OBJECTIVE_SCHEMA_VERSION,
            objective_id=objective_id or str(uuid4()),
            objective_kind=ReviewObjectiveKind.FINDING_ANALYSIS,
            review_mode=mode,
            phase_id=phase_id,
            purpose=(
                "Test the selected REVIEW finding against the frozen evidence and develop "
                "an evidence-bounded response without assuming the reviewer is correct."
            ),
            subject=ObjectiveSubject(
                subject_type=SubjectType.FINDING,
                source_id=finding_id,
                title=finding_title,
                statement=finding_statement,
                related_finding_ids=related_ids,
            ),
            evidence_refs=evidence_refs,
            required_outcomes=(
                ObjectiveOutcome.FINDING_CLAIM_CLEAR,
                ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
                ObjectiveOutcome.FINDING_ENGINEERING_IMPLICATION_CLEAR,
                ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
            ),
            optional_outcomes=(
                ObjectiveOutcome.OWNERSHIP_CLEAR,
                ObjectiveOutcome.CHANGE_OR_CLOSURE_CONDITION_CLEAR,
                ObjectiveOutcome.TRADEOFF_CLEAR,
            ),
            permitted_conclusions=(
                ObjectiveConclusion.FINDING_SUPPORTED,
                ObjectiveConclusion.FINDING_CREDIBLY_CHALLENGED,
                ObjectiveConclusion.CORRECTION_RECOMMENDED,
                ObjectiveConclusion.RISK_RESPONSE_BOUNDED,
                ObjectiveConclusion.DEFER_WITH_RATIONALE,
                ObjectiveConclusion.ADDITIONAL_EVIDENCE_REQUIRED,
                ObjectiveConclusion.UNRESOLVED_WITH_REASON,
            ),
            allows_unresolved=True,
            derivation_codes=("FINDING_REVIEW_SELECTED_FINDING", intent_code),
        )

    return ReviewObjective(
        schema_version=REVIEW_OBJECTIVE_SCHEMA_VERSION,
        objective_id=objective_id or str(uuid4()),
        objective_kind=ReviewObjectiveKind.BOARD_POSITION,
        review_mode=mode,
        phase_id=phase_id,
        purpose=(
            "Develop one defensible, phase-appropriate engineering position on the selected "
            "consequential concern, grounded in frozen evidence, or correctly bound the "
            "important uncertainty that prevents a current position."
        ),
        subject=ObjectiveSubject(
            subject_type=SubjectType.CHALLENGE,
            source_id=challenge_id,
            title=challenge_title,
            statement=challenge_statement,
        ),
        evidence_refs=evidence_refs,
        required_outcomes=(
            ObjectiveOutcome.CURRENT_POSITION_CLEAR,
            ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
            ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
            ObjectiveOutcome.ACTION_BOUNDARY_CLEAR,
            ObjectiveOutcome.OWNERSHIP_CLEAR,
            ObjectiveOutcome.CHANGE_OR_CLOSURE_CONDITION_CLEAR,
        ),
        optional_outcomes=(
            ObjectiveOutcome.UNCERTAINTY_CLEAR,
            ObjectiveOutcome.TRADEOFF_CLEAR,
        ),
        permitted_conclusions=(
            ObjectiveConclusion.DEFENSIBLE_POSITION,
            ObjectiveConclusion.UNRESOLVED_WITH_REASON,
        ),
        allows_unresolved=True,
        derivation_codes=("BOARD_REVIEW_EXISTING_CHALLENGE",),
    )


def initialize_review_control(
    objective: ReviewObjective,
    *,
    reasoning_mode: ReasoningValidationMode | str = ReasoningValidationMode.LEGACY,
    planning_mode: ReviewPlanningMode | str = ReviewPlanningMode.LEGACY,
) -> dict[str, Any]:
    reasoning = ReasoningValidationMode(reasoning_mode)
    planning = ReviewPlanningMode(planning_mode)
    return {
        "schema_version": REVIEW_CONTROL_SCHEMA_VERSION,
        "reasoning_mode": reasoning.value,
        "planning_mode": planning.value,
        "objective": objective.to_dict(),
    }


def review_control_modes(
    state: Mapping[str, Any] | None,
) -> tuple[ReasoningValidationMode, ReviewPlanningMode]:
    control = dict((state or {}).get("review_control") or {})
    if not control:
        return ReasoningValidationMode.LEGACY, ReviewPlanningMode.LEGACY
    return (
        ReasoningValidationMode(
            control.get("reasoning_mode", ReasoningValidationMode.LEGACY.value)
        ),
        ReviewPlanningMode(control.get("planning_mode", ReviewPlanningMode.LEGACY.value)),
    )


def _entry_intent_code(entry_intent: str | None) -> str:
    normalized = (entry_intent or "review").strip().lower().replace("-", "_")
    allowed = {"review", "discuss", "challenge", "resolve", "understand", "accept_or_defer"}
    if normalized not in allowed:
        normalized = "review"
    return f"FINDING_ENTRY_INTENT_{normalized.upper()}"


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _dedupe_strings(values: Sequence[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value
