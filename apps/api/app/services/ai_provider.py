from __future__ import annotations
import json
import httpx
from ..config import get_settings


class AIProvider:
    def available(self) -> bool:
        return False

    def reviewer_follow_up(self, system_prompt: str, user_prompt: str) -> dict:
        raise NotImplementedError


class OpenAIResponsesProvider(AIProvider):
    """Small Responses API adapter.

    The model is environment-configured. The application remains useful with AI disabled;
    deterministic challenge logic is the authoritative control plane and the model is used
    only for bounded Socratic follow-up/synthesis.
    """

    def __init__(self):
        self.s=get_settings()

    def available(self)->bool:
        return bool(self.s.etis_ai_enabled and self.s.openai_api_key and self.s.openai_model)

    def reviewer_follow_up(self, system_prompt: str, user_prompt: str) -> dict:
        if not self.available():
            raise RuntimeError("AI provider is not configured")
        payload={
            "model":self.s.openai_model,
            "input":[
                {"role":"system","content":[{"type":"input_text","text":system_prompt}]},
                {"role":"user","content":[{"type":"input_text","text":user_prompt}]}
            ]
        }
        headers={"Authorization":f"Bearer {self.s.openai_api_key}","Content-Type":"application/json"}
        with httpx.Client(timeout=60.0) as c:
            r=c.post(f"{self.s.openai_base_url.rstrip('/')}/responses", headers=headers, json=payload)
            r.raise_for_status()
            data=r.json()
        text=data.get("output_text")
        if not text:
            parts=[]
            for item in data.get("output",[]):
                for c in item.get("content",[]):
                    if c.get("type") in {"output_text","text"}:
                        parts.append(c.get("text", ""))
            text="\n".join(parts)
        return {"text": text or "", "provider":"openai", "model":self.s.openai_model, "response_id":data.get("id","")}
