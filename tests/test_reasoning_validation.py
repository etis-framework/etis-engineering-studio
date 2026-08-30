import json

from apps.api.app.services.reasoning_validation import (
    ReasoningStatus,
    ReasoningValidator,
    blank_reasoning_shadow,
)


class StubValidatorAI:
    def __init__(self, payload=None, exc=None, responses=None):
        self.payload = payload or {"evaluations": [], "reopens": []}
        self.exc = exc
        self.responses = list(responses or [])
        self.calls = []

    def available(self):
        return True

    def validate_reasoning_turn(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.responses:
            payload = self.responses.pop(0)
            if isinstance(payload, Exception):
                raise payload
        else:
            if self.exc:
                raise self.exc
            payload = self.payload
        response_id = f"resp-{len(self.calls)}"
        return {
            **payload,
            "provider": "stub-validator",
            "model": "validator-model",
            "response_id": response_id,
            "_usage": {
                "purpose": "reasoning_validation_shadow",
                "model": "validator-model",
                "response_id": response_id,
                "input_tokens": 10,
                "cached_input_tokens": 0,
                "cache_write_tokens": 0,
                "output_tokens": 5,
                "latency_ms": 12,
                "estimated_cost_usd": 0.001,
            },
        }


def _objective():
    return {
        "objective_id": "obj-1",
        "review_mode": "board_review",
        "phase_id": "A1",
        "purpose": "Develop a defensible position.",
        "evidence_refs": ["PATH:docs/team/roles.md"],
    }


def _validate(ai, **overrides):
    args = {
        "objective": _objective(),
        "shadow_state": blank_reasoning_shadow(),
        "proposal_updates": {"consequence_visible": True},
        "proposal_intent": "reasoning",
        "student_text": "Unclear ownership could cause finger-pointing when something fails.",
        "decision": None,
        "evidence_refs": [],
        "evidence_context": "PATH:docs/team/roles.md\nOwners are listed.",
        "conversation_history": [
            {"actor": "reviewer", "lens": "chief_architect", "content": "What consequence matters?"}
        ],
        "turn_sequence": 2,
        "client_turn_id": "turn-2",
        "operation": "respond",
        "legacy_prior": {},
        "legacy_merged": {"consequence_visible": True},
    }
    args.update(overrides)
    return ReasoningValidator(ai=ai).validate_turn(**args)


def test_blank_shadow_state_starts_unestablished():
    shadow = blank_reasoning_shadow()
    assert shadow["schema_version"] == 1
    assert all(
        item["status"] == ReasoningStatus.UNESTABLISHED.value
        for item in shadow["dimensions"].values()
    )
    assert shadow["comparison"]["completed_validations"] == 0


def test_accept_updates_shadow_without_changing_legacy_state():
    ai = StubValidatorAI(
        {
            "evaluations": [
                {
                    "dimension": "consequence_visible",
                    "decision": "ACCEPT",
                    "reason_codes": ["STUDENT_REASONING_EXPLICIT"],
                    "evidence_refs": [],
                    "summary": "The student explicitly connected unclear ownership to a consequence.",
                }
            ],
            "reopens": [],
        }
    )
    outcome = _validate(ai)

    assert outcome.signal["status"] == "completed"
    assert outcome.signal["evaluations"][0]["decision"] == "ACCEPT"
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "validated"
    assert outcome.shadow_state["comparison"]["legacy_new_grants"] == 1
    assert outcome.shadow_state["comparison"]["validator_accepts"] == 1
    assert outcome.signal["completeness_repair"]["attempted"] is False
    assert len(outcome.usage_events) == 1
    request = json.loads(ai.calls[0][1])
    assert request["response_contract"]["required_evaluation_dimensions"] == [
        "consequence_visible"
    ]
    assert request["response_contract"]["return_exactly_one_evaluation_per_required_dimension"] is True
    assert "reasoning-dimension recognition" in ai.calls[0][0]
    assert "change_trigger_visible" in ai.calls[0][0]


def test_partial_is_preserved_as_meaningful_but_incomplete_progress():
    ai = StubValidatorAI(
        {
            "evaluations": [
                {
                    "dimension": "consequence_visible",
                    "decision": "PARTIAL",
                    "reason_codes": ["TENTATIVE_BUT_MEANINGFUL"],
                    "evidence_refs": [],
                    "summary": "A consequence is suggested but not yet bounded.",
                }
            ],
            "reopens": [],
        }
    )
    outcome = _validate(ai)
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "partial"
    assert outcome.shadow_state["comparison"]["validator_partials"] == 1


def test_reject_does_not_upgrade_shadow_reasoning():
    ai = StubValidatorAI(
        {
            "evaluations": [
                {
                    "dimension": "consequence_visible",
                    "decision": "REJECT",
                    "reason_codes": ["TOO_VAGUE_TO_ESTABLISH"],
                    "evidence_refs": [],
                    "summary": "The student did not actually state the engineering consequence.",
                }
            ],
            "reopens": [],
        }
    )
    outcome = _validate(ai)
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "unestablished"
    assert outcome.shadow_state["comparison"]["validator_rejects"] == 1


def test_validator_cannot_grant_unproposed_dimension_or_unlisted_evidence():
    ai = StubValidatorAI(
        {
            "evaluations": [
                {
                    "dimension": "ownership_visible",
                    "decision": "ACCEPT",
                    "reason_codes": ["STUDENT_REASONING_EXPLICIT"],
                    "evidence_refs": ["PATH:invented.md"],
                    "summary": "Should be filtered because ownership was not proposed.",
                },
                {
                    "dimension": "consequence_visible",
                    "decision": "ACCEPT",
                    "reason_codes": ["EVIDENCE_REFERENCE_IN_SCOPE"],
                    "evidence_refs": ["PATH:invented.md", "PATH:docs/team/roles.md"],
                    "summary": "Only the authorized evidence reference may survive.",
                },
            ],
            "reopens": [],
        }
    )
    outcome = _validate(ai)
    evaluations = outcome.signal["evaluations"]
    assert [item["dimension"] for item in evaluations] == ["consequence_visible"]
    assert evaluations[0]["evidence_refs"] == ["PATH:docs/team/roles.md"]
    assert outcome.shadow_state["dimensions"]["ownership_visible"]["status"] == "unestablished"


def test_missing_validator_judgment_gets_one_repair_then_fails_closed():
    ai = StubValidatorAI({"evaluations": [], "reopens": []})
    outcome = _validate(ai)
    evaluation = outcome.signal["evaluations"][0]
    repair = outcome.signal["completeness_repair"]
    assert evaluation["decision"] == "REJECT"
    assert evaluation["reason_codes"] == ["VALIDATOR_RESULT_MISSING"]
    assert repair == {
        "attempted": True,
        "missing_before": ["consequence_visible"],
        "recovered_dimensions": [],
        "missing_after": ["consequence_visible"],
        "succeeded": False,
        "error_type": None,
    }
    assert len(ai.calls) == 2
    assert len(outcome.usage_events) == 2
    repair_request = json.loads(ai.calls[1][1])
    assert repair_request["response_contract"]["required_evaluation_dimensions"] == [
        "consequence_visible"
    ]
    assert repair_request["response_contract"]["repair_only_missing_dimensions"] is True
    assert repair_request["response_contract"]["reopens_allowed"] is False


def test_missing_validator_judgment_can_be_recovered_without_revising_first_result():
    ai = StubValidatorAI(
        responses=[
            {
                "evaluations": [
                    {
                        "dimension": "consequence_visible",
                        "decision": "ACCEPT",
                        "reason_codes": ["STUDENT_REASONING_EXPLICIT"],
                        "evidence_refs": [],
                        "summary": "The consequence is explicit.",
                    }
                ],
                "reopens": [],
            },
            {
                "evaluations": [
                    {
                        "dimension": "consequence_visible",
                        "decision": "REJECT",
                        "reason_codes": ["TOO_VAGUE_TO_ESTABLISH"],
                        "evidence_refs": [],
                        "summary": "This must not revise the first result.",
                    },
                    {
                        "dimension": "change_trigger_visible",
                        "decision": "PARTIAL",
                        "reason_codes": ["TENTATIVE_BUT_MEANINGFUL"],
                        "evidence_refs": [],
                        "summary": "A real but incomplete change trigger is stated.",
                    },
                ],
                "reopens": [
                    {
                        "dimension": "consequence_visible",
                        "new_status": "unestablished",
                        "reason_codes": ["STUDENT_CORRECTION_REOPENS"],
                        "summary": "Repair must not reopen prior reasoning.",
                    }
                ],
            },
        ]
    )
    outcome = _validate(
        ai,
        proposal_updates={
            "consequence_visible": True,
            "change_trigger_visible": True,
        },
        legacy_merged={
            "consequence_visible": True,
            "change_trigger_visible": True,
        },
    )
    evaluations = {
        item["dimension"]: item
        for item in outcome.signal["evaluations"]
    }
    assert evaluations["consequence_visible"]["decision"] == "ACCEPT"
    assert evaluations["change_trigger_visible"]["decision"] == "PARTIAL"
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "validated"
    assert outcome.shadow_state["dimensions"]["change_trigger_visible"]["status"] == "partial"
    assert outcome.signal["reopens"] == []
    assert outcome.signal["completeness_repair"] == {
        "attempted": True,
        "missing_before": ["change_trigger_visible"],
        "recovered_dimensions": ["change_trigger_visible"],
        "missing_after": [],
        "succeeded": True,
        "error_type": None,
    }
    assert len(outcome.usage_events) == 2


def test_repair_provider_failure_preserves_initial_fail_closed_result():
    ai = StubValidatorAI(
        responses=[
            {"evaluations": [], "reopens": []},
            RuntimeError("repair failed"),
        ]
    )
    outcome = _validate(ai)
    evaluation = outcome.signal["evaluations"][0]
    repair = outcome.signal["completeness_repair"]
    assert outcome.signal["status"] == "completed"
    assert evaluation["decision"] == "REJECT"
    assert evaluation["reason_codes"] == ["VALIDATOR_RESULT_MISSING"]
    assert repair["attempted"] is True
    assert repair["succeeded"] is False
    assert repair["error_type"] == "RuntimeError"
    assert repair["missing_after"] == ["consequence_visible"]
    assert len(outcome.usage_events) == 1



def test_validator_prompt_freezes_dimension_vs_evidence_and_tentative_decision_semantics():
    ai = StubValidatorAI(
        {
            "evaluations": [
                {
                    "dimension": "consequence_visible",
                    "decision": "ACCEPT",
                    "reason_codes": ["STUDENT_REASONING_EXPLICIT"],
                    "evidence_refs": [],
                    "summary": "A consequence is explicit.",
                }
            ],
            "reopens": [],
        }
    )
    _validate(ai)
    system_prompt = ai.calls[0][0]
    normalized_prompt = " ".join(system_prompt.split())
    assert "the absence of proof is not by itself a reason to return PARTIAL" in normalized_prompt
    assert "EVIDENCE_SUPPORT_NOT_ESTABLISHED is descriptive metadata rather than a downgrade reason" in normalized_prompt
    assert '"probably should," "seems okay," "maybe,"' in normalized_prompt
    assert '"resolve this before merge" can be ACCEPT' in normalized_prompt
    assert "operators have no demonstrated way to know a failure" in normalized_prompt

def test_correction_can_reopen_prior_validated_reasoning():
    shadow = blank_reasoning_shadow()
    shadow["dimensions"]["consequence_visible"].update(
        {
            "status": "validated",
            "source_turn_sequence": 2,
            "source_client_turn_id": "turn-2",
        }
    )
    ai = StubValidatorAI(
        {
            "evaluations": [],
            "reopens": [
                {
                    "dimension": "consequence_visible",
                    "new_status": "unestablished",
                    "reason_codes": ["STUDENT_CORRECTION_REOPENS"],
                    "summary": "The student explicitly withdrew the earlier consequence claim.",
                }
            ],
        }
    )
    outcome = _validate(
        ai,
        shadow_state=shadow,
        proposal_updates={},
        proposal_intent="self_correction",
        student_text="I need to correct what I said earlier; that consequence does not follow from this evidence.",
        legacy_prior={"consequence_visible": True},
        legacy_merged={"consequence_visible": True},
    )
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "unestablished"
    assert outcome.shadow_state["comparison"]["reopened_dimensions"] == 1


def test_no_material_transition_skips_model_call():
    ai = StubValidatorAI()
    outcome = _validate(
        ai,
        proposal_updates={},
        proposal_intent="reasoning",
        legacy_prior={},
        legacy_merged={},
    )
    assert outcome.signal["status"] == "skipped"
    assert outcome.signal["reason"] == "no_material_transition"
    assert ai.calls == []


def test_synthetic_coach_request_never_receives_shadow_reasoning_credit():
    ai = StubValidatorAI()
    outcome = _validate(ai, operation="coach")
    assert outcome.signal["status"] == "skipped"
    assert outcome.signal["reason"] == "synthetic_coach_request"
    assert ai.calls == []
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "unestablished"


def test_shadow_validator_failure_never_raises_into_student_turn():
    ai = StubValidatorAI(exc=RuntimeError("provider failed"))
    outcome = _validate(ai)
    assert outcome.signal["status"] == "failed"
    assert outcome.signal["error_type"] == "RuntimeError"
    assert outcome.shadow_state["comparison"]["failed_validations"] == 1
    assert outcome.shadow_state["dimensions"]["consequence_visible"]["status"] == "unestablished"
