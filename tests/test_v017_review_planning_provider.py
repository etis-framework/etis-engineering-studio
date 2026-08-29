from types import SimpleNamespace

from apps.api.app.services.ai_provider import (
    OpenAIResponsesProvider,
    REVIEW_MOVE_REALIZATION_SCHEMA,
    REVIEW_PLANNER_SCHEMA,
)
from apps.api.app.services.review_planning import (
    CandidateMoveType,
    ObjectiveOutcome,
    SelectionReasonCode,
)


def _provider():
    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        openai_review_planner_model="",
        openai_critic_model="gpt-planner",
        openai_model="gpt-conversation",
        etis_review_planner_ai_reasoning_effort="low",
    )
    return provider


def test_review_planner_uses_structured_candidate_pass_and_planner_model():
    provider = _provider()
    captured = {}

    def fake_post(system_prompt, user_prompt, schema, schema_name, **kwargs):
        captured.update({"schema": schema, "schema_name": schema_name, **kwargs})
        return {"candidates": []}

    provider._post_structured = fake_post
    assert provider.plan_review_turn("planner system", "planner user") == {"candidates": []}
    assert captured["schema"] is REVIEW_PLANNER_SCHEMA
    assert captured["schema_name"] == "etis_review_planner"
    assert captured["model"] == "gpt-planner"
    assert captured["purpose"] == "review_planning_shadow"
    assert captured["reasoning_effort"] == "low"


def test_review_move_realizer_is_separate_structured_pass_using_same_shadow_model():
    provider = _provider()
    captured = {}

    def fake_post(system_prompt, user_prompt, schema, schema_name, **kwargs):
        captured.update({"schema": schema, "schema_name": schema_name, **kwargs})
        return {"lead_in": "", "question": "What should change?"}

    provider._post_structured = fake_post
    result = provider.realize_review_move("realizer system", "realizer user")
    assert result["question"] == "What should change?"
    assert captured["schema"] is REVIEW_MOVE_REALIZATION_SCHEMA
    assert captured["schema_name"] == "etis_review_move_realizer"
    assert captured["model"] == "gpt-planner"
    assert captured["purpose"] == "review_move_realization_shadow"


def test_review_planner_model_override_applies_to_planner_and_realizer():
    provider = _provider()
    provider.s.openai_review_planner_model = "gpt-explicit-planner"
    models = []

    def fake_post(system_prompt, user_prompt, schema, schema_name, **kwargs):
        models.append(kwargs["model"])
        return {"candidates": []} if schema is REVIEW_PLANNER_SCHEMA else {"lead_in": "", "question": "Why?"}

    provider._post_structured = fake_post
    provider.plan_review_turn("s", "u")
    provider.realize_review_move("s", "u")
    assert models == ["gpt-explicit-planner", "gpt-explicit-planner"]


def test_planner_schema_stays_aligned_with_contract_enums_and_has_no_question_field():
    candidate = REVIEW_PLANNER_SCHEMA["properties"]["candidates"]["items"]
    assert set(candidate["properties"]["move_type"]["enum"]) == {item.value for item in CandidateMoveType}
    assert set(candidate["properties"]["target_outcome"]["enum"]) == {item.value for item in ObjectiveOutcome}
    assert set(candidate["properties"]["reason_codes"]["items"]["enum"]) == {item.value for item in SelectionReasonCode}
    assert "question" not in candidate["properties"]
    assert "question_drafts" not in REVIEW_PLANNER_SCHEMA["properties"]
