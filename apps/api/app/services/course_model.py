import json
from functools import lru_cache
from . import __init__  # noqa: F401
from ..config import get_settings


@lru_cache
def load_course() -> dict:
    path = get_settings().repo_root / "course-model" / "course.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_phases() -> list[dict]:
    path = get_settings().repo_root / "course-model" / "phases.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_rubrics() -> dict:
    path = get_settings().repo_root / "course-model" / "rubrics.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_phase(phase_id: str) -> dict:
    for phase in load_phases():
        if phase["id"] == phase_id:
            return phase
    raise KeyError(f"Unknown phase: {phase_id}")
