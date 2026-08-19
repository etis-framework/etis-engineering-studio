from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def _catalog():
    root = Path(__file__).resolve().parents[4]
    data = json.loads((root / "course-model" / "etis_guidance.json").read_text(encoding="utf-8"))
    return data.get("items", [])


def guidance_for(phase_id: str, target_move: str | None = None, limit: int = 3):
    matches = []
    for item in _catalog():
        if phase_id not in item.get("phase_ids", []):
            continue
        score = 1
        if target_move and target_move in item.get("moves", []):
            score += 3
        matches.append((score, item))
    matches.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _score, item in matches[:limit]]


def verified_guidance(ids: list[str] | None):
    ids = ids or []
    lookup = {item["id"]: item for item in _catalog()}
    return [lookup[x] for x in ids if x in lookup]
