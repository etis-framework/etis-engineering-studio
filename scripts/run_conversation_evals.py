#!/usr/bin/env python3
"""Optional live semantic conversation smoke-eval.

This intentionally does not run in CI because it calls the configured OpenAI API and incurs cost.
It checks that representative student utterances can be classified into an acceptable semantic
intent family. Human review of the generated coaching reply remains required for release sign-off.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

from apps.api.app.services.ai_provider import OpenAIResponsesProvider

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals" / "student_behavior_cases.json").read_text())

SYSTEM = """You are evaluating one junior-engineer utterance for the ETIS Engineering Studio. Infer intent from meaning, not punctuation or exact keywords. Return the normal reviewer-turn structured schema. Keep reply under 80 words. The repository context is illustrative and must not be invented beyond the prompt."""

ACCEPTABLE = {
    "tentative-correct": {"tentative_reasoning", "reasoning", "partial_answer"},
    "poor-spelling-correct": {"reasoning", "partial_answer"},
    "one-word": {"partial_answer", "reasoning"},
    "stuck": {"stuck"},
    "answer-seeking": {"answer_seeking"},
    "simplify": {"simplify_request", "clarification"},
    "example": {"example_request"},
    "source": {"source_request"},
    "repeat-repair": {"meta_repair"},
    "misunderstood": {"meta_misunderstood", "meta_repair"},
    "frustrated": {"frustration"},
    "combative": {"hostility", "frustration"},
    "sarcastic": {"disagreement", "humor", "reasoning"},
    "disagreement": {"disagreement", "evidence_dispute", "reasoning"},
    "evidence-dispute": {"evidence_dispute"},
    "rambling": {"rambling", "reasoning", "partial_answer"},
    "self-correction": {"self_correction", "reasoning"},
    "topic-shift": {"topic_shift"},
    "humor": {"humor", "reasoning"},
    "grading-game": {"grading_request", "answer_seeking"},
    "skip": {"skip_request", "disengaged"},
    "senior-opinion": {"answer_seeking", "clarification"},
    "overconfident": {"reasoning", "disagreement"},
    "misconception-absence": {"misconception"},
    "misconception-ci": {"misconception"},
    "polished-ungrounded": {"reasoning", "partial_answer"},
    "very-informal": {"answer_seeking", "stuck"},
    "non-native-english": {"reasoning", "partial_answer"},
    "asks-why": {"clarification"},
    "asks-reviewer-wrong": {"evidence_dispute", "disagreement"},
    "disengaged": {"disengaged", "frustration"},
}


def main() -> int:
    provider = OpenAIResponsesProvider()
    if not provider.available():
        print("Semantic provider is not configured. Set OPENAI_API_KEY in .env before running live evals.")
        return 2
    failures = 0
    for case in CASES:
        user = f"""A1 context: Maya is coaching a junior engineer about a repository governance finding. Newest student utterance: {case['utterance']}\nExpected coaching behavior: {case['behavior']}"""
        out = provider.reviewer_turn(SYSTEM, user)
        got = out.get("student_intent")
        ok = got in ACCEPTABLE.get(case["id"], {case.get("expected_intent")})
        print(("PASS" if ok else "FAIL"), case["id"], "->", got, "|", out.get("reply", "")[:160])
        failures += 0 if ok else 1
    print(f"\n{len(CASES)-failures}/{len(CASES)} semantic intent cases within acceptable families.")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
