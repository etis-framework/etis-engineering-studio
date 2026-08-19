from types import SimpleNamespace

import httpx
import pytest

from apps.api.app.services import ai_provider as ai_provider_module
from apps.api.app.services.ai_provider import OpenAIResponsesProvider


def test_openai_provider_does_not_retry_permanent_401(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            calls.append(
                {
                    "url": url,
                    "headers": dict(headers),
                    "json": json,
                }
            )
            return httpx.Response(
                401,
                request=httpx.Request("POST", url),
                json={
                    "error": {
                        "message": "Incorrect API key provided.",
                        "type": "invalid_request_error",
                    }
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(ai_provider_module.time, "sleep", lambda _: None)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    with pytest.raises(httpx.HTTPStatusError):
        provider._post_structured(
            "system prompt",
            "user prompt",
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "gate8_test",
        )

    # Permanent authentication/configuration failures must fail immediately.
    assert len(calls) == 1


def test_openai_provider_does_not_retry_credit_balance_exhausted(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            calls.append(url)
            return httpx.Response(
                429,
                request=httpx.Request("POST", url),
                json={
                    "error": {
                        "message": "Your credit balance is exhausted.",
                        "type": "insufficient_quota",
                        "code": "credit_balance_exhausted",
                    }
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(ai_provider_module.time, "sleep", lambda _: None)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    with pytest.raises(httpx.HTTPStatusError):
        provider._post_structured(
            "system prompt",
            "user prompt",
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "gate8_test",
        )

    # Billing/quota failures require operator action and must fail immediately.
    assert len(calls) == 1


def test_openai_provider_retries_transient_429_once_and_recovers(monkeypatch):
    calls = []
    sleeps = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            calls.append(url)

            if len(calls) == 1:
                return httpx.Response(
                    429,
                    request=httpx.Request("POST", url),
                    json={
                        "error": {
                            "message": "Rate limit reached.",
                            "type": "rate_limit_error",
                            "code": "rate_limit_exceeded",
                        }
                    },
                )

            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate8",
                    "output_text": "{}",
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        ai_provider_module.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    result = provider._post_structured(
        "system prompt",
        "user prompt",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "gate8_test",
    )

    assert len(calls) == 2
    assert sleeps == [0.7]
    assert result["provider"] == "openai"
    assert result["response_id"] == "resp_gate8"


def test_openai_provider_honors_retry_after_for_transient_429(monkeypatch):
    calls = []
    sleeps = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            calls.append(url)

            if len(calls) == 1:
                return httpx.Response(
                    429,
                    request=httpx.Request("POST", url),
                    headers={"Retry-After": "2"},
                    json={
                        "error": {
                            "message": "Rate limit reached.",
                            "type": "rate_limit_error",
                            "code": "rate_limit_exceeded",
                        }
                    },
                )

            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate8_retry_after",
                    "output_text": "{}",
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        ai_provider_module.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    result = provider._post_structured(
        "system prompt",
        "user prompt",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "gate8_test",
    )

    assert len(calls) == 2
    assert sleeps == [2.0]
    assert result["response_id"] == "resp_gate8_retry_after"


@pytest.mark.parametrize("status_code", [408, 409])
def test_openai_provider_retries_transient_408_and_409(monkeypatch, status_code):
    calls = []
    sleeps = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            calls.append(url)

            if len(calls) == 1:
                return httpx.Response(
                    status_code,
                    request=httpx.Request("POST", url),
                    json={
                        "error": {
                            "message": "Transient request failure.",
                            "type": "transient_error",
                        }
                    },
                )

            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": f"resp_gate8_{status_code}",
                    "output_text": "{}",
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        ai_provider_module.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    result = provider._post_structured(
        "system prompt",
        "user prompt",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "gate8_test",
    )

    assert len(calls) == 2
    assert sleeps == [0.7]
    assert result["response_id"] == f"resp_gate8_{status_code}"


def test_openai_provider_rejects_incomplete_structured_response(monkeypatch):
    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate8_incomplete",
                    "status": "incomplete",
                    "incomplete_details": {
                        "reason": "max_output_tokens",
                    },
                    # Deliberately parseable: production code must not accept
                    # this merely because it happens to be valid JSON.
                    "output_text": "{}",
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    with pytest.raises(RuntimeError, match="incomplete"):
        provider._post_structured(
            "system prompt",
            "user prompt",
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "gate8_test",
        )


def test_openai_provider_rejects_structured_output_refusal_explicitly(monkeypatch):
    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate8_refusal",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "refusal",
                                    "refusal": "I cannot assist with that request.",
                                }
                            ],
                        }
                    ],
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    with pytest.raises(RuntimeError, match="refused"):
        provider._post_structured(
            "system prompt",
            "user prompt",
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "gate8_test",
        )


def test_openai_provider_rejects_failed_structured_response(monkeypatch):
    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate8_failed",
                    "status": "failed",
                    "error": {
                        "code": "server_error",
                        "message": "Model response generation failed.",
                    },
                    # Parseable text must not override the failed lifecycle state.
                    "output_text": "{}",
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    with pytest.raises(RuntimeError, match="failed"):
        provider._post_structured(
            "system prompt",
            "user prompt",
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "gate8_test",
        )


def test_openai_provider_rejects_nonterminal_structured_response(monkeypatch):
    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate8_in_progress",
                    "status": "in_progress",
                    # Parseable text must not override nonterminal lifecycle state.
                    "output_text": "{}",
                    "usage": {},
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-ETISGATE8IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
        openai_model="gpt-5.6",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    with pytest.raises(RuntimeError, match="not completed"):
        provider._post_structured(
            "system prompt",
            "user prompt",
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "gate8_test",
        )


def test_openai_responses_disable_provider_application_state(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            calls.append(
                {
                    "url": url,
                    "headers": dict(headers),
                    "json": json,
                }
            )
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "resp_gate17_retention",
                    "status": "completed",
                    "output_text": "{}",
                    "usage": {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "total_tokens": 2,
                    },
                },
            )

    monkeypatch.setattr(ai_provider_module.httpx, "Client", FakeClient)

    provider = OpenAIResponsesProvider.__new__(OpenAIResponsesProvider)
    provider.s = SimpleNamespace(
        etis_ai_enabled=True,
        openai_api_key="sk-proj-GATE17RETENTION",
        openai_model="gpt-5.6-sol",
        etis_ai_reasoning_effort="low",
        etis_prompt_cache_enabled=False,
        etis_ai_timeout_seconds=60.0,
        openai_base_url="https://api.openai.com/v1",
    )

    provider._post_structured(
        "system prompt",
        "user prompt",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "gate17_retention",
    )

    assert len(calls) == 1
    assert calls[0]["json"].get("store") is False
