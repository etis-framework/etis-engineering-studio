from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .ai_provider import OpenAIResponsesProvider
from .model_disclosure import sanitize_model_text


REASONING_VALIDATION_SCHEMA_VERSION = 1


class ReasoningDimension(str, Enum):
    CONSEQUENCE_VISIBLE = "consequence_visible"
    EVIDENCE_BOUNDARY_VISIBLE = "evidence_boundary_visible"
    DECISION_EXPLICIT = "decision_explicit"
    BOUNDARY_VISIBLE = "boundary_visible"
    OWNERSHIP_VISIBLE = "ownership_visible"
    CHANGE_TRIGGER_VISIBLE = "change_trigger_visible"
    UNCERTAINTY_VISIBLE = "uncertainty_visible"
    TRADEOFF_VISIBLE = "tradeoff_visible"


class ValidationDecision(str, Enum):
    ACCEPT = "ACCEPT"
    PARTIAL = "PARTIAL"
    REJECT = "REJECT"


class ReasoningStatus(str, Enum):
    UNESTABLISHED = "unestablished"
    PARTIAL = "partial"
    VALIDATED = "validated"


class ValidationReasonCode(str, Enum):
    STUDENT_REASONING_EXPLICIT = "STUDENT_REASONING_EXPLICIT"
    SELECTED_DECISION_SUPPORTS_REASONING = "SELECTED_DECISION_SUPPORTS_REASONING"
    EVIDENCE_REFERENCE_IN_SCOPE = "EVIDENCE_REFERENCE_IN_SCOPE"
    EVIDENCE_SUPPORT_NOT_ESTABLISHED = "EVIDENCE_SUPPORT_NOT_ESTABLISHED"
    TENTATIVE_BUT_MEANINGFUL = "TENTATIVE_BUT_MEANINGFUL"
    TOO_VAGUE_TO_ESTABLISH = "TOO_VAGUE_TO_ESTABLISH"
    ONLY_REPEATS_REVIEWER_LANGUAGE = "ONLY_REPEATS_REVIEWER_LANGUAGE"
    REVIEWER_CLAIM_NOT_STUDENT_REASONING = "REVIEWER_CLAIM_NOT_STUDENT_REASONING"
    OUTSIDE_REVIEW_OBJECTIVE = "OUTSIDE_REVIEW_OBJECTIVE"
    UNSUPPORTED_BY_FROZEN_EVIDENCE = "UNSUPPORTED_BY_FROZEN_EVIDENCE"
    VALID_UNCERTAINTY_BOUNDED = "VALID_UNCERTAINTY_BOUNDED"
    STUDENT_CORRECTION_REOPENS = "STUDENT_CORRECTION_REOPENS"
    CURRENT_TURN_CONTRADICTS_PRIOR_STATE = "CURRENT_TURN_CONTRADICTS_PRIOR_STATE"
    VALIDATOR_RESULT_MISSING = "VALIDATOR_RESULT_MISSING"


CORRECTION_INTENTS = frozenset(
    {
        "self_correction",
        "disagreement",
        "evidence_dispute",
        "misconception",
        "meta_misunderstood",
    }
)


@dataclass(frozen=True)
class ReasoningValidationOutcome:
    signal: dict[str, Any]
    shadow_state: dict[str, Any]
    usage_events: tuple[dict[str, Any], ...] = ()


def blank_reasoning_shadow() -> dict[str, Any]:
    return {
        "schema_version": REASONING_VALIDATION_SCHEMA_VERSION,
        "dimensions": {
            dimension.value: {
                "status": ReasoningStatus.UNESTABLISHED.value,
                "source_turn_sequence": None,
                "source_client_turn_id": None,
                "evidence_refs": [],
                "reason_codes": [],
                "summary": "",
            }
            for dimension in ReasoningDimension
        },
        "comparison": {
            "completed_validations": 0,
            "skipped_validations": 0,
            "failed_validations": 0,
            "legacy_new_grants": 0,
            "validator_accepts": 0,
            "validator_partials": 0,
            "validator_rejects": 0,
            "reopened_dimensions": 0,
        },
        "last_validation": None,
    }


def ensure_reasoning_shadow(value: Mapping[str, Any] | None) -> dict[str, Any]:
    base = blank_reasoning_shadow()
    incoming = dict(value or {})
    dimensions = incoming.get("dimensions") or {}
    for dimension in ReasoningDimension:
        current = dimensions.get(dimension.value)
        if not isinstance(current, Mapping):
            continue
        status = str(current.get("status") or ReasoningStatus.UNESTABLISHED.value)
        if status not in {item.value for item in ReasoningStatus}:
            status = ReasoningStatus.UNESTABLISHED.value
        base["dimensions"][dimension.value] = {
            "status": status,
            "source_turn_sequence": current.get("source_turn_sequence"),
            "source_client_turn_id": current.get("source_client_turn_id"),
            "evidence_refs": _dedupe_strings(current.get("evidence_refs") or ()),
            "reason_codes": _dedupe_strings(current.get("reason_codes") or ()),
            "summary": str(current.get("summary") or "")[:220],
        }
    comparison = incoming.get("comparison") or {}
    for key in base["comparison"]:
        try:
            base["comparison"][key] = max(0, int(comparison.get(key, 0)))
        except (TypeError, ValueError):
            base["comparison"][key] = 0
    if isinstance(incoming.get("last_validation"), Mapping):
        base["last_validation"] = dict(incoming["last_validation"])
    return base


class ReasoningValidator:
    """Independent, shadow-only authority check for semantic reasoning proposals.

    The validator never generates student-facing dialogue and never changes the legacy
    reasoning state. It evaluates only proposed transitions plus explicit reopen
    candidates from previously shadow-validated state.
    """

    def __init__(self, ai=None):
        self.ai = ai or OpenAIResponsesProvider()

    def validate_turn(
        self,
        *,
        objective: Mapping[str, Any],
        shadow_state: Mapping[str, Any] | None,
        proposal_updates: Mapping[str, Any] | None,
        proposal_intent: str,
        student_text: str,
        decision: str | None,
        evidence_refs: Sequence[str] | None,
        evidence_context: str,
        conversation_history: Sequence[Mapping[str, Any]] | None,
        turn_sequence: int,
        client_turn_id: str | None,
        operation: str,
        legacy_prior: Mapping[str, Any] | None,
        legacy_merged: Mapping[str, Any] | None,
    ) -> ReasoningValidationOutcome:
        shadow = ensure_reasoning_shadow(shadow_state)
        candidates = _proposed_dimensions(proposal_updates)
        reopen_candidates = _reopen_candidates(shadow, proposal_intent)

        legacy_prior = dict(legacy_prior or {})
        legacy_merged = dict(legacy_merged or {})
        legacy_new = [
            dimension.value
            for dimension in ReasoningDimension
            if bool(legacy_merged.get(dimension.value))
            and not bool(legacy_prior.get(dimension.value))
        ]

        if operation == "coach":
            return _skipped_outcome(
                shadow,
                reason="synthetic_coach_request",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
                legacy_new=legacy_new,
            )

        if not candidates and not reopen_candidates:
            return _skipped_outcome(
                shadow,
                reason="no_material_transition",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
                legacy_new=legacy_new,
            )

        if not hasattr(self.ai, "validate_reasoning_turn") or not self.ai.available():
            return _failed_outcome(
                shadow,
                error_type="ValidatorUnavailable",
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
                candidates=candidates,
                legacy_new=legacy_new,
            )

        system_prompt = _validator_system_prompt()
        user_prompt = _validator_user_prompt(
            objective=objective,
            shadow=shadow,
            candidates=candidates,
            reopen_candidates=reopen_candidates,
            proposal_intent=proposal_intent,
            student_text=student_text,
            decision=decision,
            evidence_refs=evidence_refs or (),
            evidence_context=evidence_context,
            conversation_history=conversation_history or (),
        )

        try:
            parsed = self.ai.validate_reasoning_turn(system_prompt, user_prompt)
        except Exception as exc:
            return _failed_outcome(
                shadow,
                error_type=type(exc).__name__,
                turn_sequence=turn_sequence,
                client_turn_id=client_turn_id,
                operation=operation,
                candidates=candidates,
                legacy_new=legacy_new,
            )

        normalized = _normalize_validator_result(
            parsed,
            candidates=candidates,
            reopen_candidates=reopen_candidates,
            allowed_evidence_refs=_allowed_evidence_refs(objective, evidence_refs or ()),
        )
        updated = _apply_completed_validation(
            shadow,
            normalized,
            turn_sequence=turn_sequence,
            client_turn_id=client_turn_id,
            operation=operation,
            proposal_intent=proposal_intent,
            legacy_new=legacy_new,
        )
        usage = parsed.get("_usage") if isinstance(parsed, Mapping) else None
        return ReasoningValidationOutcome(
            signal=updated["last_validation"],
            shadow_state=updated,
            usage_events=(dict(usage),) if isinstance(usage, Mapping) else (),
        )


def _validator_system_prompt() -> str:
    return """
You are the independent ETIS reasoning-state validator. You do not coach the student,
select the next question, grade work, or decide engineering truth. Your only job is to
validate whether the newest STUDENT reasoning actually justifies the candidate durable
reasoning transitions proposed by a separate conversational reviewer.

Authority rules:
1. Judge the student's newest statement and any explicit structured decision they made.
2. Use only the supplied frozen evidence context and listed evidence references.
3. The reviewer's prior wording may provide conversational context but is not student reasoning.
4. Do not grant a reasoning dimension that is not listed as a candidate transition.
5. ACCEPT requires a sufficiently explicit, defensible engineering idea for this review objective.
6. PARTIAL means the student made meaningful progress but an important part remains missing.
7. REJECT means the statement is too vague, merely repeats reviewer language, is unsupported,
   outside the objective, or otherwise does not justify durable reasoning credit.
8. A tentative statement may be PARTIAL or ACCEPT when its engineering meaning is genuinely clear.
9. For reopen candidates, reopen only when the newest student statement retracts, contradicts,
   or materially corrects previously shadow-validated reasoning.
10. Legitimate bounded uncertainty is valid engineering reasoning; never turn an unknown into a known.
11. Never invent repository evidence or infer support from a path that is not supplied.
12. Return only concise structured judgments and reason codes. Do not provide chain-of-thought.
""".strip()


def _validator_user_prompt(
    *,
    objective: Mapping[str, Any],
    shadow: Mapping[str, Any],
    candidates: Sequence[str],
    reopen_candidates: Sequence[str],
    proposal_intent: str,
    student_text: str,
    decision: str | None,
    evidence_refs: Sequence[str],
    evidence_context: str,
    conversation_history: Sequence[Mapping[str, Any]],
) -> str:
    recent = []
    for turn in conversation_history[-8:]:
        recent.append(
            {
                "actor": str(turn.get("actor") or ""),
                "lens": str(turn.get("lens") or ""),
                "content": str(turn.get("content") or "")[:700],
            }
        )
    state_summary = {
        key: value.get("status")
        for key, value in (shadow.get("dimensions") or {}).items()
        if isinstance(value, Mapping)
    }
    safe_evidence = sanitize_model_text((evidence_context or "")[:7000]).text
    payload = {
        "review_objective": objective,
        "current_shadow_reasoning_status": state_summary,
        "candidate_transitions": list(candidates),
        "reopen_candidates": list(reopen_candidates),
        "conversation_interpretation_hint": proposal_intent or "other",
        "recent_transcript_before_newest_student_turn": recent,
        "newest_student_turn": str(student_text or "")[:6000],
        "student_selected_decision": str(decision or "")[:500] or None,
        "student_selected_evidence_refs": _dedupe_strings(evidence_refs)[:20],
        "frozen_evidence_context": safe_evidence,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _proposed_dimensions(updates: Mapping[str, Any] | None) -> tuple[str, ...]:
    values = dict(updates or {})
    return tuple(
        dimension.value
        for dimension in ReasoningDimension
        if bool(values.get(dimension.value))
    )


def _reopen_candidates(shadow: Mapping[str, Any], proposal_intent: str) -> tuple[str, ...]:
    if (proposal_intent or "").strip().lower() not in CORRECTION_INTENTS:
        return ()
    dimensions = shadow.get("dimensions") or {}
    return tuple(
        dimension.value
        for dimension in ReasoningDimension
        if str((dimensions.get(dimension.value) or {}).get("status"))
        in {ReasoningStatus.PARTIAL.value, ReasoningStatus.VALIDATED.value}
    )


def _allowed_evidence_refs(
    objective: Mapping[str, Any], student_refs: Sequence[str]
) -> set[str]:
    return set(_dedupe_strings([*(objective.get("evidence_refs") or []), *student_refs]))


def _normalize_validator_result(
    parsed: Mapping[str, Any],
    *,
    candidates: Sequence[str],
    reopen_candidates: Sequence[str],
    allowed_evidence_refs: set[str],
) -> dict[str, Any]:
    candidate_set = set(candidates)
    reopen_set = set(reopen_candidates)
    evaluations_by_dimension: dict[str, dict[str, Any]] = {}
    for item in parsed.get("evaluations") or []:
        if not isinstance(item, Mapping):
            continue
        dimension = str(item.get("dimension") or "")
        if dimension not in candidate_set or dimension in evaluations_by_dimension:
            continue
        decision = str(item.get("decision") or ValidationDecision.REJECT.value)
        if decision not in {entry.value for entry in ValidationDecision}:
            decision = ValidationDecision.REJECT.value
        evaluations_by_dimension[dimension] = {
            "dimension": dimension,
            "decision": decision,
            "reason_codes": _valid_reason_codes(item.get("reason_codes") or ()),
            "evidence_refs": [
                ref
                for ref in _dedupe_strings(item.get("evidence_refs") or ())
                if ref in allowed_evidence_refs
            ],
            "summary": str(item.get("summary") or "")[:220],
        }

    evaluations = []
    for dimension in candidates:
        item = evaluations_by_dimension.get(dimension)
        if item is None:
            item = {
                "dimension": dimension,
                "decision": ValidationDecision.REJECT.value,
                "reason_codes": [ValidationReasonCode.VALIDATOR_RESULT_MISSING.value],
                "evidence_refs": [],
                "summary": "Validator did not return a judgment for this proposed transition.",
            }
        evaluations.append(item)

    reopens = []
    seen_reopens: set[str] = set()
    for item in parsed.get("reopens") or []:
        if not isinstance(item, Mapping):
            continue
        dimension = str(item.get("dimension") or "")
        if dimension not in reopen_set or dimension in seen_reopens:
            continue
        new_status = str(item.get("new_status") or ReasoningStatus.UNESTABLISHED.value)
        if new_status not in {ReasoningStatus.UNESTABLISHED.value, ReasoningStatus.PARTIAL.value}:
            new_status = ReasoningStatus.UNESTABLISHED.value
        seen_reopens.add(dimension)
        reopens.append(
            {
                "dimension": dimension,
                "new_status": new_status,
                "reason_codes": _valid_reason_codes(item.get("reason_codes") or ()),
                "summary": str(item.get("summary") or "")[:220],
            }
        )

    return {
        "evaluations": evaluations,
        "reopens": reopens,
        "provider": str(parsed.get("provider") or ""),
        "model": str(parsed.get("model") or ""),
        "response_id": str(parsed.get("response_id") or ""),
    }


def _apply_completed_validation(
    shadow: Mapping[str, Any],
    normalized: Mapping[str, Any],
    *,
    turn_sequence: int,
    client_turn_id: str | None,
    operation: str,
    proposal_intent: str,
    legacy_new: Sequence[str],
) -> dict[str, Any]:
    updated = ensure_reasoning_shadow(shadow)
    dimensions = updated["dimensions"]

    for reopen in normalized.get("reopens") or []:
        dimension = reopen["dimension"]
        dimensions[dimension] = {
            "status": reopen["new_status"],
            "source_turn_sequence": turn_sequence,
            "source_client_turn_id": client_turn_id,
            "evidence_refs": [],
            "reason_codes": list(reopen.get("reason_codes") or []),
            "summary": str(reopen.get("summary") or "")[:220],
        }

    for evaluation in normalized.get("evaluations") or []:
        dimension = evaluation["dimension"]
        decision = evaluation["decision"]
        existing = dimensions[dimension]
        new_status = existing["status"]
        if decision == ValidationDecision.ACCEPT.value:
            new_status = ReasoningStatus.VALIDATED.value
        elif decision == ValidationDecision.PARTIAL.value:
            if existing["status"] != ReasoningStatus.VALIDATED.value:
                new_status = ReasoningStatus.PARTIAL.value
        elif decision == ValidationDecision.REJECT.value:
            continue
        dimensions[dimension] = {
            "status": new_status,
            "source_turn_sequence": turn_sequence,
            "source_client_turn_id": client_turn_id,
            "evidence_refs": list(evaluation.get("evidence_refs") or []),
            "reason_codes": list(evaluation.get("reason_codes") or []),
            "summary": str(evaluation.get("summary") or "")[:220],
        }

    evaluations = list(normalized.get("evaluations") or [])
    comparison = updated["comparison"]
    comparison["completed_validations"] += 1
    comparison["legacy_new_grants"] += len(legacy_new)
    comparison["validator_accepts"] += sum(
        item.get("decision") == ValidationDecision.ACCEPT.value for item in evaluations
    )
    comparison["validator_partials"] += sum(
        item.get("decision") == ValidationDecision.PARTIAL.value for item in evaluations
    )
    comparison["validator_rejects"] += sum(
        item.get("decision") == ValidationDecision.REJECT.value for item in evaluations
    )
    comparison["reopened_dimensions"] += len(normalized.get("reopens") or [])

    last = {
        "status": "completed",
        "schema_version": REASONING_VALIDATION_SCHEMA_VERSION,
        "turn_sequence": turn_sequence,
        "client_turn_id": client_turn_id,
        "operation": operation,
        "proposal_intent": proposal_intent or "other",
        "legacy_new_dimensions": list(legacy_new),
        "evaluations": evaluations,
        "reopens": list(normalized.get("reopens") or []),
        "provider": normalized.get("provider") or "",
        "model": normalized.get("model") or "",
        "response_id": normalized.get("response_id") or "",
    }
    updated["last_validation"] = last
    return updated


def _skipped_outcome(
    shadow: Mapping[str, Any],
    *,
    reason: str,
    turn_sequence: int,
    client_turn_id: str | None,
    operation: str,
    legacy_new: Sequence[str],
) -> ReasoningValidationOutcome:
    updated = ensure_reasoning_shadow(shadow)
    updated["comparison"]["skipped_validations"] += 1
    updated["comparison"]["legacy_new_grants"] += len(legacy_new)
    signal = {
        "status": "skipped",
        "schema_version": REASONING_VALIDATION_SCHEMA_VERSION,
        "turn_sequence": turn_sequence,
        "client_turn_id": client_turn_id,
        "operation": operation,
        "reason": reason,
        "legacy_new_dimensions": list(legacy_new),
    }
    updated["last_validation"] = signal
    return ReasoningValidationOutcome(signal=signal, shadow_state=updated)


def _failed_outcome(
    shadow: Mapping[str, Any],
    *,
    error_type: str,
    turn_sequence: int,
    client_turn_id: str | None,
    operation: str,
    candidates: Sequence[str],
    legacy_new: Sequence[str],
) -> ReasoningValidationOutcome:
    updated = ensure_reasoning_shadow(shadow)
    updated["comparison"]["failed_validations"] += 1
    updated["comparison"]["legacy_new_grants"] += len(legacy_new)
    signal = {
        "status": "failed",
        "schema_version": REASONING_VALIDATION_SCHEMA_VERSION,
        "turn_sequence": turn_sequence,
        "client_turn_id": client_turn_id,
        "operation": operation,
        "candidate_dimensions": list(candidates),
        "legacy_new_dimensions": list(legacy_new),
        "error_type": error_type,
    }
    updated["last_validation"] = signal
    return ReasoningValidationOutcome(signal=signal, shadow_state=updated)


def _valid_reason_codes(values: Sequence[Any]) -> list[str]:
    allowed = {entry.value for entry in ValidationReasonCode}
    return [value for value in _dedupe_strings(values) if value in allowed]


def _dedupe_strings(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
