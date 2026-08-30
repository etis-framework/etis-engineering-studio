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

        usage_events: list[dict[str, Any]] = []
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

        usage = parsed.get("_usage") if isinstance(parsed, Mapping) else None
        if isinstance(usage, Mapping):
            usage_events.append(dict(usage))

        allowed_evidence_refs = _allowed_evidence_refs(
            objective,
            evidence_refs or (),
        )
        normalized = _normalize_validator_result(
            parsed,
            candidates=candidates,
            reopen_candidates=reopen_candidates,
            allowed_evidence_refs=allowed_evidence_refs,
        )

        missing_before = _missing_validator_dimensions(normalized)
        repair_telemetry = {
            "attempted": False,
            "missing_before": list(missing_before),
            "recovered_dimensions": [],
            "missing_after": list(missing_before),
            "succeeded": None,
            "error_type": None,
        }

        if missing_before:
            repair_telemetry["attempted"] = True
            repair_prompt = _validator_user_prompt(
                objective=objective,
                shadow=shadow,
                candidates=missing_before,
                reopen_candidates=(),
                proposal_intent=proposal_intent,
                student_text=student_text,
                decision=decision,
                evidence_refs=evidence_refs or (),
                evidence_context=evidence_context,
                conversation_history=conversation_history or (),
                repair_only_missing=True,
            )
            try:
                repaired = self.ai.validate_reasoning_turn(
                    system_prompt,
                    repair_prompt,
                )
            except Exception as exc:
                repair_telemetry["succeeded"] = False
                repair_telemetry["error_type"] = type(exc).__name__
            else:
                repair_usage = (
                    repaired.get("_usage")
                    if isinstance(repaired, Mapping)
                    else None
                )
                if isinstance(repair_usage, Mapping):
                    usage_events.append(dict(repair_usage))
                repair_normalized = _normalize_validator_result(
                    repaired,
                    candidates=missing_before,
                    reopen_candidates=(),
                    allowed_evidence_refs=allowed_evidence_refs,
                )
                normalized, recovered = _merge_validator_repair(
                    normalized,
                    repair_normalized,
                    missing_before=missing_before,
                )
                missing_after = _missing_validator_dimensions(normalized)
                repair_telemetry["recovered_dimensions"] = list(recovered)
                repair_telemetry["missing_after"] = list(missing_after)
                repair_telemetry["succeeded"] = not missing_after

        normalized["completeness_repair"] = repair_telemetry
        updated = _apply_completed_validation(
            shadow,
            normalized,
            turn_sequence=turn_sequence,
            client_turn_id=client_turn_id,
            operation=operation,
            proposal_intent=proposal_intent,
            legacy_new=legacy_new,
        )
        return ReasoningValidationOutcome(
            signal=updated["last_validation"],
            shadow_state=updated,
            usage_events=tuple(usage_events),
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
7. REJECT means the statement is too vague, merely repeats reviewer language, is outside the
   objective, directly conflicts with frozen evidence, or otherwise does not justify durable credit.
8. Separate reasoning-dimension recognition from proof of every factual premise. A student can
   explicitly demonstrate a consequence, boundary, trigger, uncertainty, or other reasoning move
   while frozen evidence still leaves the underlying premise incomplete. In that situation, use
   EVIDENCE_SUPPORT_NOT_ESTABLISHED or UNSUPPORTED_BY_FROZEN_EVIDENCE as appropriate, but do not
   automatically erase or downgrade an otherwise explicit reasoning dimension. For
   evidence_boundary_visible especially, the fact that support is missing, stale, contradictory,
   or unverified may be the boundary the student is correctly identifying; the absence of proof is
   not by itself a reason to return PARTIAL. ACCEPT never converts the student's claim into
   repository FACT.
9. A tentative statement may be PARTIAL or ACCEPT when its engineering meaning is genuinely clear.
10. For reopen candidates, reopen only when the newest student statement retracts, contradicts,
    or materially corrects previously shadow-validated reasoning.
11. Legitimate bounded uncertainty is valid engineering reasoning; never turn an unknown into a known.
12. Never invent repository evidence or infer support from a path that is not supplied.
13. Return exactly one evaluation for every required candidate dimension and no evaluation for any
    other dimension. Do not silently omit a required judgment.
14. Return only concise structured judgments and reason codes. Do not provide chain-of-thought.

Reasoning-dimension meanings:
- consequence_visible: the student states a meaningful engineering effect, impact, failure, delay,
  blocked dependency, operational outcome, or other consequence. A directly stated operational
  inability or exposure (for example, that operators have no demonstrated way to know a failure
  occurred) can be ACCEPT without requiring the student to restate the obvious effect using the word
  "therefore."
- evidence_boundary_visible: the student distinguishes what current evidence establishes from what
  it does not establish. Exact artifact-name recitation is not required when the boundary itself is
  explicit and bounded; generic "we need more evidence" language is insufficient. When the student
  explicitly identifies evidence as stale, contradictory, missing, unverified, or unable to support
  a claim, EVIDENCE_SUPPORT_NOT_ESTABLISHED is descriptive metadata rather than a downgrade reason.
  Return PARTIAL or REJECT only when the boundary itself is vague, merely inferred, fabricated, or
  contradicted by supplied frozen evidence.
- decision_explicit: the student actually states an adopted current engineering position or choice.
  A hedge or inclination such as "probably should," "seems okay," "maybe," or merely saying an
  action is possible is at most PARTIAL unless the student clearly adopts the position.
- boundary_visible: the student identifies a meaningful action, scope, decision, stop, escalation,
  or revision boundary. A clear hold/stop condition such as "resolve this before merge" can be ACCEPT
  even when the exact remediation choice remains open. PARTIAL is appropriate when only a general
  direction is visible and the operative boundary itself remains unclear.
- ownership_visible: the student identifies who owns a decision, verification, correction, or
  follow-through. Merely naming who authored work, including a teammate or AI, is not ownership.
- change_trigger_visible: the student identifies an observable condition, evidence change, or event
  that causes a position, plan, artifact, or action to change or close. A change that has already
  occurred may satisfy this dimension when the student explicitly connects it to the required revision.
- uncertainty_visible: the student identifies a bounded unknown rather than converting it into
  certainty. Stronger reasoning also explains why the unknown matters or how it can be resolved.
- tradeoff_visible: the student identifies competing engineering value/benefit and downside/cost/risk.
  A threshold, trigger, consequence, or risk by itself is not automatically a tradeoff.
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
    repair_only_missing: bool = False,
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
        "response_contract": {
            "required_evaluation_dimensions": list(candidates),
            "return_exactly_one_evaluation_per_required_dimension": True,
            "return_no_other_evaluation_dimensions": True,
            "reopens_allowed": bool(reopen_candidates) and not repair_only_missing,
            "repair_only_missing_dimensions": bool(repair_only_missing),
        },
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


def _missing_validator_dimensions(
    normalized: Mapping[str, Any],
) -> tuple[str, ...]:
    return tuple(
        str(item.get("dimension") or "")
        for item in (normalized.get("evaluations") or ())
        if isinstance(item, Mapping)
        and ValidationReasonCode.VALIDATOR_RESULT_MISSING.value
        in set(item.get("reason_codes") or ())
        and str(item.get("dimension") or "")
    )


def _merge_validator_repair(
    initial: Mapping[str, Any],
    repair: Mapping[str, Any],
    *,
    missing_before: Sequence[str],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    allowed = set(missing_before)
    repaired_by_dimension = {
        str(item.get("dimension") or ""): dict(item)
        for item in (repair.get("evaluations") or ())
        if isinstance(item, Mapping)
        and str(item.get("dimension") or "") in allowed
        and ValidationReasonCode.VALIDATOR_RESULT_MISSING.value
        not in set(item.get("reason_codes") or ())
    }

    merged = dict(initial)
    evaluations: list[dict[str, Any]] = []
    recovered: list[str] = []
    for item in initial.get("evaluations") or ():
        current = dict(item)
        dimension = str(current.get("dimension") or "")
        replacement = repaired_by_dimension.get(dimension)
        if (
            replacement is not None
            and ValidationReasonCode.VALIDATOR_RESULT_MISSING.value
            in set(current.get("reason_codes") or ())
        ):
            current = replacement
            recovered.append(dimension)
        evaluations.append(current)
    merged["evaluations"] = evaluations
    return merged, tuple(recovered)


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
        "completeness_repair": dict(
            normalized.get("completeness_repair") or {}
        ),
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
