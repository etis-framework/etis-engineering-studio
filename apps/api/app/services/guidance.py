from __future__ import annotations

import json
import re
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


def guidance_for_topic(phase_id: str, question: str, target_move: str | None = None,
                       limit: int = 3):
    """Choose a verified course reference for the student's actual question."""
    choices = guidance_for(phase_id, target_move, limit=20)
    preferred = None
    if phase_id == 'A1':
        preferred = ('ETIS-ES101-CONTEXT' if re.search(
            r'\b(problem|scope|stakeholder|success|outcome|launch)\b', question, re.I)
            else 'ETIS-ES100-PRINCIPLES' if re.search(
                r'\b(owner|decision|authority|escalat|govern)', question, re.I) else None)
    elif phase_id == 'A2':
        preferred = ('ETIS-ES103-CONTEXT' if re.search(
            r'\b(plan|estimat|schedule|task|dependenc|risk|re.estimat)', question, re.I)
            else 'ETIS-ES102-READINESS' if re.search(
                r'\b(requirement|constraint|acceptance)', question, re.I) else None)
    if preferred:
        choices.sort(key=lambda item: item['id'] != preferred)
    return choices[:limit]


def verified_guidance(ids: list[str] | None):
    ids = ids or []
    lookup = {item["id"]: item for item in _catalog()}
    return [lookup[x] for x in ids if x in lookup]
