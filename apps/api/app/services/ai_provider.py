from __future__ import annotations

import json
import time
import hashlib
import httpx
from ..config import get_settings
from .ai_telemetry import usage_from_response


CONVERSATION_SCHEMA = {
    "type": "object",
    "properties": {
        "student_intent": {
            "type": "string",
            "enum": [
                "reasoning", "tentative_reasoning", "partial_answer", "clarification", "stuck", "answer_seeking",
                "example_request", "source_request", "disagreement", "evidence_dispute", "meta_repair",
                "meta_misunderstood", "frustration", "humor", "rambling", "self_correction",
                "topic_shift", "disengaged", "misconception", "simplify_request", "grading_request", "skip_request", "hostility",
                "privacy_request", "prompt_injection", "future_phase_request", "refresh_request", "reviewer_request", "safety_concern",
                "language_support", "ambiguous_expression", "authority_claim", "process_question", "professional_boundary",
                "senior_opinion_request", "resolution_help", "new_session_focus", "other"
            ],
        },
        "understood_points": {"type": "array", "items": {"type": "string"}},
        "reasoning_updates": {
            "type": "object",
            "properties": {
                "consequence_visible": {"type": "boolean"},
                "evidence_boundary_visible": {"type": "boolean"},
                "decision_explicit": {"type": "boolean"},
                "boundary_visible": {"type": "boolean"},
                "ownership_visible": {"type": "boolean"},
                "change_trigger_visible": {"type": "boolean"},
                "uncertainty_visible": {"type": "boolean"},
                "tradeoff_visible": {"type": "boolean"},
            },
            "required": [
                "consequence_visible", "evidence_boundary_visible", "decision_explicit", "boundary_visible",
                "ownership_visible", "change_trigger_visible", "uncertainty_visible", "tradeoff_visible"
            ],
            "additionalProperties": False,
        },
        "stuck": {"type": "boolean"},
        "frustrated": {"type": "boolean"},
        "needs_direct_teaching": {"type": "boolean"},
        "response_mode": {
            "type": "string",
            "enum": ["coach", "teach", "repair", "clarify", "challenge", "confirm", "explain"],
        },
        "next_target": {
            "anyOf": [
                {"type": "string", "enum": [
                    "consequence_visible", "evidence_boundary_visible", "decision_explicit", "boundary_visible",
                    "ownership_visible", "change_trigger_visible", "uncertainty_visible", "tradeoff_visible"
                ]},
                {"type": "null"},
            ]
        },
        "reply": {"type": "string"},
        "guidance_ids": {"type": "array", "items": {"type": "string"}},
        "handoff_lens": {
            "anyOf": [
                {"type": "string", "enum": ["evidence_auditor", "chief_architect", "delivery", "red_team"]},
                {"type": "null"},
            ]
        },
        "teach_back": {"type": "boolean"},
    },
    "required": [
        "student_intent", "understood_points", "reasoning_updates", "stuck", "frustrated",
        "needs_direct_teaching", "response_mode", "next_target", "reply", "guidance_ids",
        "handoff_lens", "teach_back"
    ],
    "additionalProperties": False,
}



REASONING_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                        "enum": [
                            "consequence_visible", "evidence_boundary_visible", "decision_explicit",
                            "boundary_visible", "ownership_visible", "change_trigger_visible",
                            "uncertainty_visible", "tradeoff_visible"
                        ],
                    },
                    "decision": {"type": "string", "enum": ["ACCEPT", "PARTIAL", "REJECT"]},
                    "reason_codes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "STUDENT_REASONING_EXPLICIT",
                                "SELECTED_DECISION_SUPPORTS_REASONING",
                                "EVIDENCE_REFERENCE_IN_SCOPE",
                                "EVIDENCE_SUPPORT_NOT_ESTABLISHED",
                                "TENTATIVE_BUT_MEANINGFUL",
                                "TOO_VAGUE_TO_ESTABLISH",
                                "ONLY_REPEATS_REVIEWER_LANGUAGE",
                                "REVIEWER_CLAIM_NOT_STUDENT_REASONING",
                                "OUTSIDE_REVIEW_OBJECTIVE",
                                "UNSUPPORTED_BY_FROZEN_EVIDENCE",
                                "VALID_UNCERTAINTY_BOUNDED",
                                "STUDENT_CORRECTION_REOPENS",
                                "CURRENT_TURN_CONTRADICTS_PRIOR_STATE",
                                "VALIDATOR_RESULT_MISSING"
                            ],
                        },
                    },
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string", "maxLength": 220},
                },
                "required": ["dimension", "decision", "reason_codes", "evidence_refs", "summary"],
                "additionalProperties": False,
            },
        },
        "reopens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                        "enum": [
                            "consequence_visible", "evidence_boundary_visible", "decision_explicit",
                            "boundary_visible", "ownership_visible", "change_trigger_visible",
                            "uncertainty_visible", "tradeoff_visible"
                        ],
                    },
                    "new_status": {"type": "string", "enum": ["unestablished", "partial"]},
                    "reason_codes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "STUDENT_REASONING_EXPLICIT",
                                "SELECTED_DECISION_SUPPORTS_REASONING",
                                "EVIDENCE_REFERENCE_IN_SCOPE",
                                "EVIDENCE_SUPPORT_NOT_ESTABLISHED",
                                "TENTATIVE_BUT_MEANINGFUL",
                                "TOO_VAGUE_TO_ESTABLISH",
                                "ONLY_REPEATS_REVIEWER_LANGUAGE",
                                "REVIEWER_CLAIM_NOT_STUDENT_REASONING",
                                "OUTSIDE_REVIEW_OBJECTIVE",
                                "UNSUPPORTED_BY_FROZEN_EVIDENCE",
                                "VALID_UNCERTAINTY_BOUNDED",
                                "STUDENT_CORRECTION_REOPENS",
                                "CURRENT_TURN_CONTRADICTS_PRIOR_STATE",
                                "VALIDATOR_RESULT_MISSING"
                            ],
                        },
                    },
                    "summary": {"type": "string", "maxLength": 220},
                },
                "required": ["dimension", "new_status", "reason_codes", "summary"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["evaluations", "reopens"],
    "additionalProperties": False,
}


REPOSITORY_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": {"type": "array", "items": {"type": "string"}},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": [
                        "weak_evidence", "contradiction", "traceability_break", "unsupported_claim",
                        "risk_blindness", "ownership_ambiguity", "ai_governance_gap", "artifact_theater",
                        "engineering_tradeoff", "workflow_gap", "release_control", "operational_gap"
                    ]},
                    "title": {"type": "string"},
                    "statement": {"type": "string"},
                    "significance": {"type": "string"},
                    "severity": {"type": "integer", "minimum": 1, "maximum": 5},
                    "confidence": {"type": "string", "enum": ["low", "moderate", "high"]},
                    "evidence_paths": {"type": "array", "items": {"type": "string"}},
                    "suggested_lens": {"type": "string", "enum": ["evidence_auditor", "chief_architect", "delivery", "red_team"]},
                },
                "required": ["category", "title", "statement", "significance", "severity", "confidence", "evidence_paths", "suggested_lens"],
                "additionalProperties": False,
            },
        },
        "equivalent_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "expected_path": {"type": "string"},
                    "actual_path": {"type": "string"},
                    "explanation": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "moderate", "high"]},
                },
                "required": ["expected_path", "actual_path", "explanation", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["strengths", "findings", "equivalent_evidence"],
    "additionalProperties": False,
}

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "acceptable": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "revised_reply": {"type": "string"},
    },
    "required": ["acceptable", "issues", "revised_reply"],
    "additionalProperties": False,
}


class AIProvider:
    def available(self) -> bool:
        return False

    def reviewer_turn(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError

    def critique_reviewer_turn(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError

    def repository_assessment(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError

    def validate_reasoning_turn(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError


class OpenAIResponsesProvider(AIProvider):
    """Responses API adapter using Structured Outputs.

    The model performs semantic interpretation and natural coaching. The application
    retains deterministic authority over phase contracts, evidence, verified guidance,
    and commit readiness. A second critic pass can reject/rewrite a draft that ignores
    the student's latest message, repeats itself, or fails to teach when rescue is needed.
    """

    def __init__(self):
        self.s = get_settings()

    def available(self) -> bool:
        return bool(self.s.etis_ai_enabled and self.s.openai_api_key and self.s.openai_model)

    def _response_text(self, data: dict) -> str:
        text = data.get("output_text")
        if text:
            return text
        parts = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    parts.append(content.get("text", ""))
        return "\n".join(x for x in parts if x)

    def _post_structured(self, system_prompt: str, user_prompt: str, schema: dict, schema_name: str, *, model: str | None = None, purpose: str = "conversation", reasoning_effort: str | None = None) -> dict:
        if not self.available():
            raise RuntimeError("Semantic coaching provider is not configured")
        selected_model = model or self.s.openai_model
        effort = reasoning_effort or self.s.etis_ai_reasoning_effort
        payload = {
            "model": selected_model,
            "store": False,
            "reasoning": {"effort": effort},
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        if self.s.etis_prompt_cache_enabled:
            stable = f"{purpose}|{selected_model}|{schema_name}|{system_prompt[:6000]}"
            payload["prompt_cache_key"] = "etis-" + hashlib.sha256(stable.encode("utf-8")).hexdigest()[:48]
        headers = {"Authorization": f"Bearer {self.s.openai_api_key}", "Content-Type": "application/json"}
        last_error = None
        started = time.perf_counter()
        with httpx.Client(timeout=self.s.etis_ai_timeout_seconds) as client:
            for attempt in range(2):
                try:
                    response = client.post(f"{self.s.openai_base_url.rstrip('/')}/responses", headers=headers, json=payload)
                    retryable_status = response.status_code in {408, 409, 500, 502, 503, 504}

                    if response.status_code == 429:
                        retryable_status = True
                        try:
                            error = response.json().get("error") or {}
                            error_type = str(error.get("type") or "").lower()
                            error_code = str(error.get("code") or "").lower()

                            if (
                                error_type == "insufficient_quota"
                                or error_code in {
                                    "insufficient_quota",
                                    "credit_balance_exhausted",
                                }
                            ):
                                retryable_status = False
                        except (ValueError, TypeError, AttributeError):
                            pass

                    if retryable_status and attempt == 0:
                        retry_delay = 0.7

                        if response.status_code == 429:
                            retry_after = response.headers.get("Retry-After")
                            if retry_after:
                                try:
                                    parsed_delay = float(retry_after)
                                    if parsed_delay > 0:
                                        retry_delay = parsed_delay
                                except ValueError:
                                    pass

                        time.sleep(retry_delay)
                        continue
                    response.raise_for_status()
                    data = response.json()

                    response_status = str(data.get("status") or "").lower()
                    if response_status == "incomplete":
                        details = data.get("incomplete_details") or {}
                        reason = str(details.get("reason") or "unknown")
                        raise RuntimeError(
                            f"OpenAI structured response incomplete: {reason}"
                        )

                    if response_status == "failed":
                        error = data.get("error") or {}
                        code = str(error.get("code") or "unknown")
                        raise RuntimeError(
                            f"OpenAI structured response failed: {code}"
                        )

                    if response_status and response_status != "completed":
                        raise RuntimeError(
                            f"OpenAI structured response not completed: {response_status}"
                        )

                    refused = any(
                        isinstance(content, dict)
                        and content.get("type") == "refusal"
                        for output in (data.get("output") or [])
                        if isinstance(output, dict)
                        for content in (output.get("content") or [])
                    )
                    if refused:
                        raise RuntimeError(
                            "OpenAI structured response was refused"
                        )

                    break
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt == 0:
                        time.sleep(0.7)
                        continue
                    raise
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    raise
            else:
                raise RuntimeError("Semantic provider request failed") from last_error
        latency_ms = int((time.perf_counter() - started) * 1000)
        text = self._response_text(data).strip()
        if not text:
            raise RuntimeError("Semantic coaching provider returned no structured output")
        parsed = json.loads(text)
        parsed["provider"] = "openai"
        parsed["model"] = selected_model
        parsed["response_id"] = data.get("id", "")
        parsed["_usage"] = usage_from_response(data, selected_model, purpose, latency_ms).to_dict()
        return parsed

    def reviewer_turn(self, system_prompt: str, user_prompt: str) -> dict:
        return self._post_structured(
            system_prompt, user_prompt, CONVERSATION_SCHEMA, "etis_reviewer_turn",
            model=self.s.openai_model, purpose="review_conversation", reasoning_effort=self.s.etis_ai_reasoning_effort
        )

    def critique_reviewer_turn(self, system_prompt: str, user_prompt: str) -> dict:
        return self._post_structured(
            system_prompt, user_prompt, CRITIC_SCHEMA, "etis_reviewer_critic",
            model=self.s.openai_critic_model, purpose="conversation_critic", reasoning_effort=self.s.etis_critic_ai_reasoning_effort
        )

    def repository_assessment(self, system_prompt: str, user_prompt: str) -> dict:
        return self._post_structured(
            system_prompt, user_prompt, REPOSITORY_ASSESSMENT_SCHEMA, "etis_repository_assessment",
            model=self.s.openai_repository_model, purpose="repository_semantic_analysis", reasoning_effort=self.s.etis_repository_ai_reasoning_effort
        )

    def validate_reasoning_turn(self, system_prompt: str, user_prompt: str) -> dict:
        model = self.s.openai_reasoning_validator_model or self.s.openai_critic_model or self.s.openai_model
        return self._post_structured(
            system_prompt, user_prompt, REASONING_VALIDATION_SCHEMA, "etis_reasoning_validation",
            model=model, purpose="reasoning_validation_shadow",
            reasoning_effort=self.s.etis_reasoning_validator_ai_reasoning_effort
        )
