from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable

# Public OpenAI API token rates observed 2026-08-15. Keep versioned and editable;
# never make release logic depend on price. Rates are USD per 1M text tokens.
RATE_CARD_VERSION = "openai-public-2026-08-15"
RATE_CARD = {
    "gpt-5.6": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
    "gpt-5.6-sol": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
    "gpt-5.6-terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00},
    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
}


@dataclass
class UsageSummary:
    model: str
    purpose: str
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    response_id: str = ""
    estimated_cost_usd: float = 0.0
    rate_card_version: str = RATE_CARD_VERSION

    def to_dict(self):
        return asdict(self)


def estimate_cost(model: str, input_tokens: int, cached_tokens: int, output_tokens: int, cache_write_tokens: int = 0) -> float:
    rates = RATE_CARD.get(model) or RATE_CARD.get("gpt-5.6")
    normal_input = max(0, input_tokens - cached_tokens - cache_write_tokens)
    # OpenAI prompt-cache writes are currently billed at 1.25x ordinary input.
    dollars = (
        normal_input * rates["input"]
        + cached_tokens * rates["cached_input"]
        + cache_write_tokens * rates["input"] * 1.25
        + output_tokens * rates["output"]
    ) / 1_000_000
    return round(dollars, 6)


def usage_from_response(data: dict, model: str, purpose: str, latency_ms: int = 0) -> UsageSummary:
    usage = data.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    cached = int(details.get("cached_tokens") or 0)
    cache_write = int(details.get("cache_write_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return UsageSummary(
        model=model,
        purpose=purpose,
        input_tokens=input_tokens,
        cached_input_tokens=cached,
        cache_write_tokens=cache_write,
        output_tokens=output_tokens,
        latency_ms=int(latency_ms or 0),
        response_id=str(data.get("id") or ""),
        estimated_cost_usd=estimate_cost(model, input_tokens, cached, output_tokens, cache_write),
    )


def merge_usage(events: Iterable[dict] | None) -> dict:
    rows = [x for x in (events or []) if isinstance(x, dict)]
    return {
        "calls": len(rows),
        "input_tokens": sum(int(x.get("input_tokens") or 0) for x in rows),
        "cached_input_tokens": sum(int(x.get("cached_input_tokens") or 0) for x in rows),
        "cache_write_tokens": sum(int(x.get("cache_write_tokens") or 0) for x in rows),
        "output_tokens": sum(int(x.get("output_tokens") or 0) for x in rows),
        "latency_ms": sum(int(x.get("latency_ms") or 0) for x in rows),
        "estimated_cost_usd": round(sum(float(x.get("estimated_cost_usd") or 0) for x in rows), 6),
    }
