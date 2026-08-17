from __future__ import annotations

import json
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import AIUsageEvent
from ..config import get_settings
from .ai_telemetry import RATE_CARD_VERSION


def record_usage_events(db: Session, events: list[dict] | None, *, team_id=None, user_id=None, session_id=None, phase_id="", metadata=None):
    if not events or not get_settings().etis_ai_usage_enabled:
        return
    for event in events:
        if not isinstance(event, dict):
            continue
        db.add(AIUsageEvent(
            course_namespace=get_settings().etis_course_namespace,
            team_id=team_id,
            user_id=user_id,
            session_id=session_id,
            phase_id=phase_id or "",
            purpose=str(event.get("purpose") or "unknown"),
            model=str(event.get("model") or ""),
            response_id=str(event.get("response_id") or ""),
            input_tokens=int(event.get("input_tokens") or 0),
            cached_input_tokens=int(event.get("cached_input_tokens") or 0),
            cache_write_tokens=int(event.get("cache_write_tokens") or 0),
            output_tokens=int(event.get("output_tokens") or 0),
            latency_ms=int(event.get("latency_ms") or 0),
            estimated_cost_microusd=int(round(float(event.get("estimated_cost_usd") or 0) * 1_000_000)),
            metadata_json=json.dumps({"rate_card": RATE_CARD_VERSION, **(metadata or {})}),
        ))


def _usage_bucket(rows):
    cost = sum(r.estimated_cost_microusd for r in rows) / 1_000_000
    total_latency = sum(r.latency_ms for r in rows)
    sorted_latency = sorted(int(r.latency_ms or 0) for r in rows)
    p95 = 0
    if sorted_latency:
        p95 = sorted_latency[min(len(sorted_latency) - 1, max(0, int(round(len(sorted_latency) * .95)) - 1))]
    total_input = sum(r.input_tokens for r in rows)
    total_cached = sum(r.cached_input_tokens for r in rows)
    return {
        "calls": len(rows),
        "input_tokens": total_input,
        "cached_input_tokens": total_cached,
        "cache_write_tokens": sum(r.cache_write_tokens for r in rows),
        "output_tokens": sum(r.output_tokens for r in rows),
        "latency_ms": total_latency,
        "avg_latency_ms": round(total_latency / max(1, len(rows))),
        "p95_latency_ms": p95,
        "estimated_cost_usd": round(cost, 4),
        "cache_hit_ratio": round(total_cached / max(1, total_input), 3),
    }


def usage_summary(db: Session, *, team_id=None, team_ids=None, phase_id=None):
    q = db.query(AIUsageEvent)
    if team_id is not None:
        q = q.filter(AIUsageEvent.team_id == team_id)
    elif team_ids is not None:
        ids=list(team_ids)
        q = q.filter(AIUsageEvent.team_id.in_(ids)) if ids else q.filter(AIUsageEvent.id == -1)
    if phase_id:
        q = q.filter(AIUsageEvent.phase_id == phase_id)
    rows = q.all()
    summary = _usage_bucket(rows)
    by_purpose = {}
    by_model = {}
    for row in rows:
        by_purpose.setdefault(row.purpose or "unknown", []).append(row)
        by_model.setdefault(row.model or "unknown", []).append(row)
    summary.update({
        "by_purpose": {k: _usage_bucket(v) for k, v in sorted(by_purpose.items())},
        "by_model": {k: _usage_bucket(v) for k, v in sorted(by_model.items())},
        "rate_card_version": RATE_CARD_VERSION,
    })
    return summary
