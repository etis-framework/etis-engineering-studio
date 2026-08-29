#!/usr/bin/env python3
"""Optional live v0.17 analytical-engine evaluation.

This runner intentionally does not run in CI. It calls the configured OpenAI API
and therefore incurs latency/cost. It evaluates the PR2 reasoning validator and
PR3 Review Planner independently against the committed A1-A6 war-game corpus.

Examples:

    python scripts/run_analytical_engine_evals.py --phase A3
    python scripts/run_analytical_engine_evals.py --tag correct_student_challenge
    python scripts/run_analytical_engine_evals.py --case a4-ci-green-overconfidence
    python scripts/run_analytical_engine_evals.py --output artifacts/analytical-eval.json

Use --blind-output plus --blind-key-output to create a randomized human review
packet comparing the legacy and shadow questions without revealing which is which.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.services.ai_provider import OpenAIResponsesProvider
from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.services.next_question_selector import allowed_evidence_refs
from apps.api.app.services.reasoning_validation import ReasoningValidator, blank_reasoning_shadow
from apps.api.app.services.review_planner import ReviewPlanner, blank_planning_shadow
from scripts.analytical_eval_support import (
    build_legacy_challenge,
    build_legacy_conversation_history,
    build_legacy_conversation_memory,
    build_legacy_reasoning_state,
    build_objective,
    build_planning_context,
    filter_cases,
    load_cases,
    reasoning_probe,
    score_planning_signal,
    score_reasoning_signal,
)

RUBRIC_PATH = ROOT / "evals" / "analytical_engine_rubric.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live ETIS v0.17 analytical-engine evals.")
    parser.add_argument("--phase", choices=[f"A{i}" for i in range(1, 7)])
    parser.add_argument("--case", action="append", dest="case_ids", default=[])
    parser.add_argument("--tag", action="append", dest="tags", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-reasoning", action="store_true")
    parser.add_argument("--skip-planning", action="store_true")
    parser.add_argument(
        "--fixture-current-question",
        action="store_true",
        help="Use the committed representative legacy question instead of calling the live current conversation engine.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--blind-output", type=Path)
    parser.add_argument("--blind-key-output", type=Path)
    parser.add_argument("--blind-seed", type=int, default=33017)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = filter_cases(load_cases(), phase=args.phase, case_ids=args.case_ids, tags=args.tags)
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("No analytical evaluation cases matched the requested filters.")
        return 2

    provider = OpenAIResponsesProvider()
    if not provider.available():
        print("OpenAI provider is not configured. Set OPENAI_API_KEY and normal ETIS AI settings before live evals.")
        return 2

    current_engine = ChallengeEngine(ai=provider)
    validator = ReasoningValidator(ai=provider)
    planner = ReviewPlanner(ai=provider)
    results: list[dict[str, Any]] = []

    for index, case in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] {case['id']} ({case['phase_id']} {case['review_mode']})")
        result: dict[str, Any] = {
            "case_id": case["id"],
            "phase_id": case["phase_id"],
            "review_mode": case["review_mode"],
            "tags": case.get("tags", []),
        }
        current_view = dict(case.get("legacy_engine") or {})
        if args.fixture_current_question:
            result["current"] = {
                "source": "fixture",
                "question": str(current_view.get("question") or ""),
                "reply": str(current_view.get("question") or ""),
                "target_move": str(current_view.get("target_move") or ""),
                "reviewer_lens": str(current_view.get("reviewer_lens") or ""),
                "usage_events": [],
            }
        else:
            result["current"] = _run_current_case(current_engine, case)
            current_view.update({
                "question": result["current"]["question"],
                "target_move": result["current"]["target_move"],
                "reviewer_lens": result["current"]["reviewer_lens"],
            })
        result["legacy_question"] = result["current"]["question"]
        print("  current:", result["current"]["source"], result["current"]["target_move"] or "no-target")

        if not args.skip_reasoning:
            result["reasoning"] = _run_reasoning_case(validator, case)
            print("  reasoning:", "PASS" if result["reasoning"]["score"]["pass"] else "FAIL")

        if not args.skip_planning:
            result["planning"] = _run_planning_case(planner, case, current_view)
            print("  planning:", "PASS" if result["planning"]["score"]["pass"] else "FAIL")

        result["hard_failures"] = _detect_hard_failures(case, result)
        if result["hard_failures"]:
            print("  HARD:", ", ".join(result["hard_failures"]))
        results.append(result)

    report = _report(results)
    _print_summary(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Wrote evaluation report: {args.output}")

    if args.blind_output or args.blind_key_output:
        if not args.blind_output or not args.blind_key_output:
            print("Both --blind-output and --blind-key-output are required together.")
            return 2
        _write_blind_packet(
            results,
            {str(case["id"]): case for case in rows},
            args.blind_output,
            args.blind_key_output,
            args.blind_seed,
        )
        print(f"Wrote blind review packet: {args.blind_output}")
        print(f"Wrote blind answer key: {args.blind_key_output}")

    thresholds = json.loads(RUBRIC_PATH.read_text())["machine_acceptance"]
    hard_count = report["summary"]["hard_failure_count"]
    reasoning_ok = args.skip_reasoning or _meets_thresholds(
        report["summary"].get("reasoning_pass_rate"),
        report["by_phase"],
        "reasoning_pass_rate",
        thresholds["reasoning_oracle_overall_min"],
        thresholds["reasoning_oracle_each_phase_min"],
    )
    planning_ok = args.skip_planning or _meets_thresholds(
        report["summary"].get("planning_move_pass_rate"),
        report["by_phase"],
        "planning_move_pass_rate",
        thresholds["planner_acceptable_move_overall_min"],
        thresholds["planner_acceptable_move_each_phase_min"],
    )
    question_ok = args.skip_planning or (
        report["summary"].get("realized_question_valid_rate") is not None
        and float(report["summary"]["realized_question_valid_rate"])
        >= float(thresholds["realized_question_machine_valid_min"])
    )
    return 0 if (
        hard_count <= thresholds["hard_failure_count_max"]
        and reasoning_ok
        and planning_ok
        and question_ok
    ) else 1


def _run_current_case(engine: ChallengeEngine, case: Mapping[str, Any]) -> dict[str, Any]:
    student = dict(case.get("student") or {})
    reviewer, _, _ = engine.converse(
        build_legacy_challenge(case),
        str(student.get("turn") or ""),
        prior_state=build_legacy_reasoning_state(case),
        intent=str(student.get("intent") or "discuss"),
        decision=str(student.get("decision") or "") or None,
        evidence_refs=tuple(student.get("evidence_refs") or ()),
        coaching_level=1,
        evidence_context=json.dumps(case.get("evidence_package") or {}, ensure_ascii=False),
        conversation_history=build_legacy_conversation_history(case),
        conversation_memory=build_legacy_conversation_memory(case),
        student_name="Student",
        allow_fallback=False,
    )
    reply = str(reviewer.get("text") or "").strip()
    return {
        "source": "live_current_engine",
        "question": _extract_main_question(reply),
        "reply": reply,
        "target_move": str(reviewer.get("target_move") or ""),
        "reviewer_lens": str(reviewer.get("lens") or ""),
        "usage_events": list(reviewer.get("usage_events") or ()),
    }


def _extract_main_question(text: str) -> str:
    text = str(text or "").strip()
    questions = re.findall(r"(?:^|(?<=[.!]))\s*([^?]+\?)", text, flags=re.MULTILINE)
    return questions[-1].strip() if questions else text


def _run_reasoning_case(validator: ReasoningValidator, case: Mapping[str, Any]) -> dict[str, Any]:
    objective = build_objective(case)
    updates, _ = reasoning_probe(case)
    student = dict(case.get("student") or {})
    evidence_context = json.dumps(case.get("evidence_package") or {}, ensure_ascii=False)
    legacy_prior = {key: False for key in updates}
    legacy_merged = {key: bool(value) for key, value in updates.items()}
    outcome = validator.validate_turn(
        objective=objective.to_dict(),
        shadow_state=blank_reasoning_shadow(),
        proposal_updates=updates,
        proposal_intent=str(student.get("intent") or "reasoning"),
        student_text=str(student.get("turn") or ""),
        decision=str(student.get("decision") or "") or None,
        evidence_refs=tuple(student.get("evidence_refs") or ()),
        evidence_context=evidence_context,
        conversation_history=(),
        turn_sequence=1,
        client_turn_id=f"eval-{case['id']}",
        operation="respond",
        legacy_prior=legacy_prior,
        legacy_merged=legacy_merged,
    )
    return {
        "score": score_reasoning_signal(case, outcome.signal),
        "signal": outcome.signal,
        "usage_events": list(outcome.usage_events),
    }


def _run_planning_case(
    planner: ReviewPlanner, case: Mapping[str, Any], current_engine: Mapping[str, Any]
) -> dict[str, Any]:
    outcome = planner.plan_turn(
        context=build_planning_context(case),
        shadow_state=blank_planning_shadow(),
        current_engine=dict(current_engine),
        turn_sequence=1,
        client_turn_id=f"eval-{case['id']}",
        operation="respond",
    )
    return {
        "score": score_planning_signal(case, outcome.signal),
        "signal": outcome.signal,
        "usage_events": list(outcome.usage_events),
    }


def _detect_hard_failures(case: Mapping[str, Any], result: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    planning = dict(result.get("planning") or {})
    signal = dict(planning.get("signal") or {})
    shadow = dict(signal.get("shadow_planner") or {})
    move = str(shadow.get("selected_move_type") or "")
    question = str(shadow.get("proposed_question") or "")
    refs = {str(value) for value in (shadow.get("evidence_refs") or ())}
    allowed_refs = set(allowed_evidence_refs(build_planning_context(case)))

    if refs - allowed_refs:
        failures.append("UNAUTHORIZED_EVIDENCE_REFERENCE")
    if _mentions_future_phase(question, str(case.get("phase_id") or "")):
        failures.append("FUTURE_PHASE_DEMAND")
    lower = question.lower()
    if any(term in lower for term in ("full credit", "grade", "points", "rubric score")):
        failures.append("HIDDEN_GRADING_BEHAVIOR")
    if any(term in lower for term in ("chain of thought", "system prompt", "hidden reasoning")):
        failures.append("CHAIN_OF_THOUGHT_EXPOSURE")
    if "correct_student_challenge" in set(case.get("tags") or ()) and move not in {
        "ADDRESS_STUDENT_CHALLENGE", "TEST_FINDING_SUPPORT", "RECONCILE_CONTRADICTION"
    }:
        failures.append("IGNORES_CORRECT_STUDENT_CHALLENGE")
    if "legitimate_unknown" in set(case.get("tags") or ()) and move in {"SYNTHESIZE_OBJECTIVE"}:
        failures.append("FALSE_CERTAINTY_FROM_LEGITIMATE_UNKNOWN")
    return sorted(set(failures))


def _mentions_future_phase(text: str, phase: str) -> bool:
    current_match = re.fullmatch(r"A([1-6])", phase.upper())
    if not current_match:
        return False
    current = int(current_match.group(1))
    return any(int(value) > current for value in re.findall(r"\bA([1-6])\b", text.upper()))


def _rate(passed: int, total: int) -> float | None:
    return round(passed / total, 4) if total else None


def _report(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "case_count": len(results),
        "hard_failure_count": sum(len(row.get("hard_failures") or ()) for row in results),
    }
    reasoning_rows = [row for row in results if "reasoning" in row]
    planning_rows = [row for row in results if "planning" in row]
    summary["reasoning_pass_rate"] = _rate(
        sum(bool(row["reasoning"]["score"]["pass"]) for row in reasoning_rows), len(reasoning_rows)
    )
    summary["planning_pass_rate"] = _rate(
        sum(bool(row["planning"]["score"]["pass"]) for row in planning_rows), len(planning_rows)
    )
    summary["planning_move_pass_rate"] = _rate(
        sum(bool(row["planning"]["score"]["move_pass"]) for row in planning_rows), len(planning_rows)
    )
    summary["planning_explicit_move_match_rate"] = _rate(
        sum(bool(row["planning"]["score"].get("explicit_move_match")) for row in planning_rows),
        len(planning_rows),
    )
    summary["planning_preferred_move_match_rate"] = _rate(
        sum(bool(row["planning"]["score"].get("preferred_move_match")) for row in planning_rows),
        len(planning_rows),
    )
    summary["realized_question_valid_rate"] = _rate(
        sum(bool(row["planning"]["score"]["question_ok"]) for row in planning_rows), len(planning_rows)
    )

    by_phase: dict[str, dict[str, Any]] = {}
    for phase in [f"A{i}" for i in range(1, 7)]:
        phase_rows = [row for row in results if row["phase_id"] == phase]
        r_rows = [row for row in phase_rows if "reasoning" in row]
        p_rows = [row for row in phase_rows if "planning" in row]
        by_phase[phase] = {
            "case_count": len(phase_rows),
            "reasoning_pass_rate": _rate(sum(bool(row["reasoning"]["score"]["pass"]) for row in r_rows), len(r_rows)),
            "planning_pass_rate": _rate(sum(bool(row["planning"]["score"]["pass"]) for row in p_rows), len(p_rows)),
            "planning_move_pass_rate": _rate(
                sum(bool(row["planning"]["score"]["move_pass"]) for row in p_rows), len(p_rows)
            ),
            "planning_explicit_move_match_rate": _rate(
                sum(bool(row["planning"]["score"].get("explicit_move_match")) for row in p_rows),
                len(p_rows),
            ),
            "planning_preferred_move_match_rate": _rate(
                sum(bool(row["planning"]["score"].get("preferred_move_match")) for row in p_rows),
                len(p_rows),
            ),
            "realized_question_valid_rate": _rate(
                sum(bool(row["planning"]["score"]["question_ok"]) for row in p_rows), len(p_rows)
            ),
            "hard_failure_count": sum(len(row.get("hard_failures") or ()) for row in phase_rows),
        }

    usage = Counter()
    latency = defaultdict(list)
    usage_totals: dict[str, Counter[str]] = defaultdict(Counter)
    usage_cost: Counter[str] = Counter()
    for row in results:
        for family in ("current", "reasoning", "planning"):
            for event in (row.get(family) or {}).get("usage_events") or ():
                purpose = str(event.get("purpose") or family)
                usage[purpose] += 1
                usage_totals[purpose]["input_tokens"] += int(event.get("input_tokens") or 0)
                usage_totals[purpose]["cached_input_tokens"] += int(event.get("cached_input_tokens") or 0)
                usage_totals[purpose]["cache_write_tokens"] += int(event.get("cache_write_tokens") or 0)
                usage_totals[purpose]["output_tokens"] += int(event.get("output_tokens") or 0)
                usage_cost[purpose] += float(event.get("estimated_cost_usd") or 0)
                if event.get("latency_ms") is not None:
                    latency[purpose].append(int(event["latency_ms"]))
    summary["usage_call_counts"] = dict(usage)
    summary["latency_ms"] = {
        purpose: {
            "count": len(values),
            "median": sorted(values)[len(values) // 2],
            "p95": sorted(values)[max(0, int(len(values) * 0.95) - 1)],
        }
        for purpose, values in latency.items()
        if values
    }
    summary["usage_by_purpose"] = {
        purpose: {
            "calls": usage[purpose],
            "input_tokens": int(usage_totals[purpose]["input_tokens"]),
            "cached_input_tokens": int(usage_totals[purpose]["cached_input_tokens"]),
            "cache_write_tokens": int(usage_totals[purpose]["cache_write_tokens"]),
            "output_tokens": int(usage_totals[purpose]["output_tokens"]),
            "estimated_cost_usd": round(float(usage_cost[purpose]), 6),
            "median_latency_ms": (
                sorted(latency[purpose])[len(latency[purpose]) // 2] if latency[purpose] else None
            ),
            "p95_latency_ms": (
                sorted(latency[purpose])[max(0, int(len(latency[purpose]) * 0.95) - 1)]
                if latency[purpose] else None
            ),
        }
        for purpose in sorted(usage)
    }
    summary["estimated_cost_usd"] = round(sum(float(value) for value in usage_cost.values()), 6)
    return {"schema_version": 1, "summary": summary, "by_phase": by_phase, "results": results}


def _print_summary(report: Mapping[str, Any]) -> None:
    summary = report["summary"]
    print("\nAnalytical engine evaluation summary")
    print("  cases:", summary["case_count"])
    print("  reasoning pass rate:", summary.get("reasoning_pass_rate"))
    print("  planning pass rate:", summary.get("planning_pass_rate"))
    print("  planning move pass rate:", summary.get("planning_move_pass_rate"))
    print("  explicit move oracle match rate:", summary.get("planning_explicit_move_match_rate"))
    print("  preferred move match rate:", summary.get("planning_preferred_move_match_rate"))
    print("  realized question valid rate:", summary.get("realized_question_valid_rate"))
    print("  hard failures:", summary["hard_failure_count"])
    for phase, values in report["by_phase"].items():
        if values["case_count"]:
            print(
                f"  {phase}: reasoning={values['reasoning_pass_rate']} "
                f"planning={values['planning_pass_rate']} hard={values['hard_failure_count']}"
            )


def _meets_thresholds(
    overall: float | None,
    by_phase: Mapping[str, Mapping[str, Any]],
    metric: str,
    overall_min: float,
    phase_min: float,
) -> bool:
    if overall is None or overall < overall_min:
        return False
    observed = [values.get(metric) for values in by_phase.values() if values.get("case_count")]
    return all(value is not None and float(value) >= phase_min for value in observed)


def _write_blind_packet(
    results: list[dict[str, Any]],
    cases_by_id: Mapping[str, Mapping[str, Any]],
    packet_path: Path,
    key_path: Path,
    seed: int,
) -> None:
    rubric = json.loads(RUBRIC_PATH.read_text())
    dimension_template = {str(item["id"]): None for item in rubric["human_dimensions"]}
    rng = random.Random(seed)
    packet = []
    key = []
    for packet_index, row in enumerate(results, start=1):
        planning = dict(row.get("planning") or {})
        signal = dict(planning.get("signal") or {})
        shadow_question = str((signal.get("shadow_planner") or {}).get("proposed_question") or "").strip()
        current_question = str(row.get("legacy_question") or "").strip()
        if not shadow_question or not current_question:
            continue
        case = cases_by_id.get(str(row["case_id"]))
        if not case:
            raise ValueError(f"missing case context for blind packet: {row['case_id']}")
        options = [("current", current_question), ("shadow", shadow_question)]
        rng.shuffle(options)
        labels = {"A": options[0], "B": options[1]}
        review_id = f"R{packet_index:03d}"
        packet.append(
            {
                "review_id": review_id,
                "phase_id": row["phase_id"],
                "review_mode": row["review_mode"],
                "case_context": _blind_case_context(case),
                "question_A": labels["A"][1],
                "question_B": labels["B"][1],
                "preference": "",
                "hard_failures": {"A": [], "B": []},
                "dimension_scores": {
                    "A": dict(dimension_template),
                    "B": dict(dimension_template),
                },
                "reviewer_notes": "",
            }
        )
        key.append(
            {
                "review_id": review_id,
                "case_id": row["case_id"],
                "current_source": str((row.get("current") or {}).get("source") or "unknown"),
                "A": labels["A"][0],
                "B": labels["B"][0],
            }
        )
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet, indent=2) + "\n")
    key_path.write_text(json.dumps(key, indent=2) + "\n")


def _blind_case_context(case: Mapping[str, Any]) -> dict[str, Any]:
    objective = build_objective(case)
    context = dict(case.get("context") or {})
    return {
        "scenario": dict(case.get("scenario") or {}),
        "review_objective": objective.to_dict(),
        "challenge": dict(case.get("challenge") or {}),
        "frozen_evidence": dict(case.get("evidence_package") or {}),
        "student": dict(case.get("student") or {}),
        "validated_reasoning": dict(case.get("validated_reasoning") or {}),
        "recent_questions": list(context.get("recent_questions") or ()),
        "recent_student_turns": list(context.get("recent_student_turns") or ()),
        "current_findings": [dict(item) for item in (context.get("current_findings") or ())],
        "finding_states": [dict(item) for item in (context.get("finding_states") or ())],
        "reviewer_corrections": [dict(item) for item in (context.get("reviewer_corrections") or ())],
        "evidence_disputes": [dict(item) for item in (context.get("evidence_disputes") or ())],
        "explicit_uncertainty": list(context.get("explicit_uncertainty") or ()),
        "assistance_state": dict(context.get("assistance_state") or {}),
    }


if __name__ == "__main__":
    raise SystemExit(main())
