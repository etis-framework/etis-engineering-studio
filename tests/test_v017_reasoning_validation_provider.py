from types import SimpleNamespace

from apps.api.app.services.ai_provider import (
    OpenAIResponsesProvider,
    REASONING_VALIDATION_SCHEMA,
)
from apps.api.app.services.reasoning_validation import (
    ReasoningDimension,
    ValidationReasonCode,
)


def test_reasoning_validator_uses_independent_structured_pass_and_validator_model():
    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        openai_reasoning_validator_model="",
        openai_critic_model="gpt-validator",
        openai_model="gpt-conversation",
        etis_reasoning_validator_ai_reasoning_effort="low",
    )
    captured = {}

    def fake_post(system_prompt, user_prompt, schema, schema_name, **kwargs):
        captured.update(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "schema": schema,
                "schema_name": schema_name,
                **kwargs,
            }
        )
        return {"evaluations": [], "reopens": []}

    provider._post_structured = fake_post
    result = provider.validate_reasoning_turn("validator system", "validator user")

    assert result == {"evaluations": [], "reopens": []}
    assert captured["schema"] is REASONING_VALIDATION_SCHEMA
    assert captured["schema_name"] == "etis_reasoning_validation"
    assert captured["model"] == "gpt-validator"
    assert captured["purpose"] == "reasoning_validation_shadow"
    assert captured["reasoning_effort"] == "low"


def test_reasoning_validator_allows_explicit_validator_model_override():
    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        openai_reasoning_validator_model="gpt-explicit-validator",
        openai_critic_model="gpt-validator",
        openai_model="gpt-conversation",
        etis_reasoning_validator_ai_reasoning_effort="medium",
    )
    captured = {}

    def fake_post(system_prompt, user_prompt, schema, schema_name, **kwargs):
        captured.update(kwargs)
        return {"evaluations": [], "reopens": []}

    provider._post_structured = fake_post
    provider.validate_reasoning_turn("validator system", "validator user")
    assert captured["model"] == "gpt-explicit-validator"
    assert captured["reasoning_effort"] == "medium"


def test_provider_schema_stays_aligned_with_validator_contract_enums():
    evaluation = REASONING_VALIDATION_SCHEMA["properties"]["evaluations"]["items"]
    dimensions = set(evaluation["properties"]["dimension"]["enum"])
    reason_codes = set(evaluation["properties"]["reason_codes"]["items"]["enum"])
    assert dimensions == {item.value for item in ReasoningDimension}
    assert reason_codes == {item.value for item in ValidationReasonCode}
