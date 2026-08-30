#!/usr/bin/env python3
"""v0.17 analytical-engine acquisition, replay, and stability evaluation.

Live acquisition intentionally does not run in CI because it calls the configured
OpenAI API and therefore incurs latency/cost. Replay and comparison operate only
on sealed captured observations and make no model calls. The runner evaluates the
PR2 reasoning validator and PR3 Review Planner against the committed A1-A6 corpus.

Examples:

    python scripts/run_analytical_engine_evals.py --phase A3
    python scripts/run_analytical_engine_evals.py --tag correct_student_challenge
    python scripts/run_analytical_engine_evals.py --case a4-ci-green-overconfidence
    python scripts/run_analytical_engine_evals.py --output artifacts/analytical-eval.json
    python scripts/run_analytical_engine_evals.py --acquisition-output artifacts/acquisition.json --output artifacts/analytical-eval.json
    python scripts/run_analytical_engine_evals.py --replay-acquisition artifacts/acquisition.json --output artifacts/replay.json

Use --blind-output plus --blind-key-output to create a randomized human review
packet comparing the legacy and shadow questions without revealing which is which.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import re
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

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
CASES_PATH = ROOT / "evals" / "analytical_engine_cases.json"
ACQUISITION_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acquire, replay, and compare ETIS v0.17 analytical-engine evaluations."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--replay-acquisition",
        type=Path,
        help="Replay/rescore a previously captured acquisition without model calls.",
    )
    mode.add_argument(
        "--compare-acquisition",
        action="append",
        dest="compare_acquisitions",
        type=Path,
        default=[],
        help="Compare two or more acquisition files for run-to-run stability. Repeat the option per file.",
    )
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
    parser.add_argument(
        "--cases-path",
        type=Path,
        default=CASES_PATH,
        help="Evaluation corpus used for live acquisition or current-oracle replay.",
    )
    parser.add_argument(
        "--replay-oracle",
        choices=("captured", "current"),
        default="captured",
        help="Score replayed observations against the captured case snapshot or the current corpus oracle.",
    )
    parser.add_argument(
        "--replicates",
        type=int,
        default=1,
        help="Number of independent live acquisitions to capture for each selected case set.",
    )
    parser.add_argument(
        "--acquisition-output",
        type=Path,
        help="Write immutable raw acquisition data. Replicated runs are stored as an acquisition set.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--stability-output",
        type=Path,
        help="Write run-to-run stability analysis for replicated or compared acquisitions.",
    )
    parser.add_argument("--blind-output", type=Path)
    parser.add_argument("--blind-key-output", type=Path)
    parser.add_argument("--blind-seed", type=int, default=33017)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.replay_acquisition:
        return _main_replay(args)
    if args.compare_acquisitions:
        return _main_compare(args)
    return _main_live(args)


def _main_live(args: argparse.Namespace) -> int:
    if args.replicates < 1:
        print("--replicates must be at least 1.")
        return 2
    if args.replicates > 1 and not args.acquisition_output:
        print("Replicated live evaluation requires --acquisition-output so every observation is preserved.")
        return 2
    if args.replicates > 1 and (args.blind_output or args.blind_key_output):
        print("Blind A/B packet generation requires exactly one acquisition. Use replay on the chosen acquisition instead.")
        return 2

    rows = filter_cases(
        load_cases(args.cases_path),
        phase=args.phase,
        case_ids=args.case_ids,
        tags=args.tags,
    )
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("No analytical evaluation cases matched the requested filters.")
        return 2

    provider = OpenAIResponsesProvider()
    if not provider.available():
        print("OpenAI provider is not configured. Set OPENAI_API_KEY and normal ETIS AI settings before live evals.")
        return 2

    acquisitions: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for replicate in range(1, args.replicates + 1):
        if args.replicates > 1:
            print(f"\n=== LIVE ACQUISITION {replicate}/{args.replicates} ===")
        acquisition = _acquire_live(provider, rows, args, replicate_index=replicate)
        report = _score_acquisition(acquisition, oracle_source="captured")
        acquisitions.append(acquisition)
        reports.append(report)
        _print_summary(report)

    if args.acquisition_output:
        payload: dict[str, Any]
        if len(acquisitions) == 1:
            payload = acquisitions[0]
        else:
            payload = _seal_payload({
                "schema_version": ACQUISITION_SCHEMA_VERSION,
                "kind": "analytical_eval_acquisition_set",
                "acquisition_count": len(acquisitions),
                "acquisitions": acquisitions,
            })
        _write_json(args.acquisition_output, payload)
        print(f"Wrote analytical acquisition: {args.acquisition_output}")

    if len(reports) == 1:
        report_payload: dict[str, Any] = reports[0]
    else:
        stability = _stability_report(acquisitions, reports)
        report_payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "kind": "analytical_eval_replicated_report",
            "replicate_count": len(reports),
            "stability": stability,
            "reports": reports,
        }
        _print_stability(stability)
        if args.stability_output:
            _write_json(args.stability_output, stability)
            print(f"Wrote stability report: {args.stability_output}")

    if args.output:
        _write_json(args.output, report_payload)
        print(f"Wrote evaluation report: {args.output}")

    if args.blind_output or args.blind_key_output:
        if not args.blind_output or not args.blind_key_output:
            print("Both --blind-output and --blind-key-output are required together.")
            return 2
        _write_blind_packet(
            reports[0]["results"],
            {str(case["id"]): case for case in rows},
            args.blind_output,
            args.blind_key_output,
            args.blind_seed,
        )
        print(f"Wrote blind review packet: {args.blind_output}")
        print(f"Wrote blind answer key: {args.blind_key_output}")

    return 0 if all(_report_passes(report) for report in reports) else 1


def _main_replay(args: argparse.Namespace) -> int:
    acquisitions = _load_acquisitions(args.replay_acquisition)
    oracle_cases: Mapping[str, Mapping[str, Any]] | None = None
    oracle_sha: str | None = None
    oracle_git_sha: str | None = None
    if args.replay_oracle == "current":
        current_rows = load_cases(args.cases_path)
        oracle_cases = {str(case["id"]): case for case in current_rows}
        oracle_sha = _sha256_file(args.cases_path)
        oracle_git_sha = _git_head()

    reports = [
        _score_acquisition(
            acquisition,
            oracle_source=args.replay_oracle,
            current_oracle_cases=oracle_cases,
            current_oracle_sha256=oracle_sha,
            current_oracle_git_sha=oracle_git_sha,
        )
        for acquisition in acquisitions
    ]
    for report in reports:
        _print_summary(report)

    if len(reports) == 1:
        payload: dict[str, Any] = reports[0]
    else:
        stability = _stability_report(acquisitions, reports)
        payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "kind": "analytical_eval_replay_set_report",
            "replicate_count": len(reports),
            "stability": stability,
            "reports": reports,
        }
        _print_stability(stability)
        if args.stability_output:
            _write_json(args.stability_output, stability)
            print(f"Wrote stability report: {args.stability_output}")

    if args.output:
        _write_json(args.output, payload)
        print(f"Wrote replay report: {args.output}")

    if args.blind_output or args.blind_key_output:
        if len(reports) != 1:
            print("Blind A/B packet generation requires replaying exactly one acquisition.")
            return 2
        if not args.blind_output or not args.blind_key_output:
            print("Both --blind-output and --blind-key-output are required together.")
            return 2
        acquisition = acquisitions[0]
        cases_by_id = {
            str(row["case_id"]): dict(row["case_snapshot"])
            for row in acquisition.get("cases") or ()
        }
        if args.replay_oracle == "current" and oracle_cases is not None:
            cases_by_id = {str(k): dict(v) for k, v in oracle_cases.items()}
        _write_blind_packet(
            reports[0]["results"],
            cases_by_id,
            args.blind_output,
            args.blind_key_output,
            args.blind_seed,
        )
        print(f"Wrote blind review packet: {args.blind_output}")
        print(f"Wrote blind answer key: {args.blind_key_output}")

    return 0 if all(_report_passes(report) for report in reports) else 1


def _main_compare(args: argparse.Namespace) -> int:
    if len(args.compare_acquisitions) < 2:
        print("Provide --compare-acquisition at least twice.")
        return 2
    acquisitions: list[dict[str, Any]] = []
    for path in args.compare_acquisitions:
        acquisitions.extend(_load_acquisitions(path))
    if len(acquisitions) < 2:
        print("At least two acquisitions are required for stability comparison.")
        return 2

    oracle_cases: Mapping[str, Mapping[str, Any]] | None = None
    oracle_sha: str | None = None
    oracle_git_sha: str | None = None
    if args.replay_oracle == "current":
        current_rows = load_cases(args.cases_path)
        oracle_cases = {str(case["id"]): case for case in current_rows}
        oracle_sha = _sha256_file(args.cases_path)
        oracle_git_sha = _git_head()
    reports = [
        _score_acquisition(
            acquisition,
            oracle_source=args.replay_oracle,
            current_oracle_cases=oracle_cases,
            current_oracle_sha256=oracle_sha,
            current_oracle_git_sha=oracle_git_sha,
        )
        for acquisition in acquisitions
    ]
    stability = _stability_report(acquisitions, reports)
    _print_stability(stability)
    target = args.stability_output or args.output
    if target:
        _write_json(target, stability)
        print(f"Wrote stability report: {target}")
    return 0


def _acquire_live(
    provider: OpenAIResponsesProvider,
    rows: Sequence[Mapping[str, Any]],
    args: argparse.Namespace,
    *,
    replicate_index: int,
) -> dict[str, Any]:
    current_engine = ChallengeEngine(ai=provider)
    validator = ReasoningValidator(ai=provider)
    planner = ReviewPlanner(ai=provider)
    records: list[dict[str, Any]] = []

    for index, case in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] {case['id']} ({case['phase_id']} {case['review_mode']})")
        record: dict[str, Any] = {
            "case_id": case["id"],
            "phase_id": case["phase_id"],
            "review_mode": case["review_mode"],
            "tags": list(case.get("tags") or ()),
            "case_snapshot": dict(case),
        }
        current_view = dict(case.get("legacy_engine") or {})
        if args.fixture_current_question:
            record["current"] = {
                "source": "fixture",
                "question": str(current_view.get("question") or ""),
                "reply": str(current_view.get("question") or ""),
                "target_move": str(current_view.get("target_move") or ""),
                "reviewer_lens": str(current_view.get("reviewer_lens") or ""),
                "interpreted_intent": str((case.get("student") or {}).get("intent") or "other"),
                "teach_back": False,
                "kind": "conversation",
                "usage_events": [],
            }
        else:
            record["current"] = _run_current_case(current_engine, case)
            current_view.update({
                "question": record["current"]["question"],
                "target_move": record["current"]["target_move"],
                "reviewer_lens": record["current"]["reviewer_lens"],
                "interpreted_intent": record["current"].get("interpreted_intent"),
                "teach_back": record["current"].get("teach_back", False),
                "kind": record["current"].get("kind"),
            })
        record["legacy_question"] = record["current"]["question"]
        print("  current:", record["current"]["source"], record["current"]["target_move"] or "no-target")

        if not args.skip_reasoning:
            record["reasoning"] = _run_reasoning_case(validator, case)
            print("  reasoning: acquired")
        if not args.skip_planning:
            record["planning"] = _run_planning_case(planner, case, current_view)
            print("  planning: acquired")
        records.append(record)

    provenance = {
        "git_commit_sha": _git_head(),
        "corpus_path": str(Path(args.cases_path)),
        "corpus_sha256": _sha256_file(args.cases_path),
        "runner_sha256": _sha256_file(Path(__file__)),
        "support_sha256": _sha256_file(ROOT / "scripts" / "analytical_eval_support.py"),
        "python_version": platform.python_version(),
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "replicate_index": replicate_index,
        "fixture_current_question": bool(args.fixture_current_question),
        "skip_reasoning": bool(args.skip_reasoning),
        "skip_planning": bool(args.skip_planning),
        "selected_case_ids": [str(case["id"]) for case in rows],
        "models_by_purpose": _models_by_purpose(records),
    }
    provenance["model_identity_status"] = (
        "reported_by_usage_events" if provenance["models_by_purpose"] else "not_reported_by_usage_events"
    )
    acquisition = {
        "schema_version": ACQUISITION_SCHEMA_VERSION,
        "kind": "analytical_eval_acquisition",
        "acquisition_id": _new_acquisition_id(),
        "provenance": provenance,
        "cases": records,
    }
    return _seal_payload(acquisition)


def _score_acquisition(
    acquisition: Mapping[str, Any],
    *,
    oracle_source: str,
    current_oracle_cases: Mapping[str, Mapping[str, Any]] | None = None,
    current_oracle_sha256: str | None = None,
    current_oracle_git_sha: str | None = None,
) -> dict[str, Any]:
    _verify_sealed_payload(acquisition)
    if oracle_source not in {"captured", "current"}:
        raise ValueError(f"unsupported oracle source: {oracle_source}")
    if oracle_source == "current" and current_oracle_cases is None:
        raise ValueError("current oracle replay requires current_oracle_cases")

    results: list[dict[str, Any]] = []
    for raw in acquisition.get("cases") or ():
        record = dict(raw)
        case_id = str(record.get("case_id") or "")
        if oracle_source == "captured":
            case = dict(record.get("case_snapshot") or {})
        else:
            supplied = current_oracle_cases.get(case_id) if current_oracle_cases else None
            if not supplied:
                raise ValueError(f"current oracle is missing acquisition case {case_id!r}")
            case = dict(supplied)

        result: dict[str, Any] = {
            "case_id": case_id,
            "phase_id": str(record.get("phase_id") or case.get("phase_id") or ""),
            "review_mode": str(record.get("review_mode") or case.get("review_mode") or ""),
            "tags": list(record.get("tags") or case.get("tags") or ()),
            "current": dict(record.get("current") or {}),
            "legacy_question": str(record.get("legacy_question") or ""),
        }
        if "reasoning" in record:
            raw_reasoning = dict(record.get("reasoning") or {})
            result["reasoning"] = {
                "score": score_reasoning_signal(case, raw_reasoning.get("signal") or {}),
                "signal": raw_reasoning.get("signal") or {},
                "usage_events": list(raw_reasoning.get("usage_events") or ()),
            }
        if "planning" in record:
            raw_planning = dict(record.get("planning") or {})
            result["planning"] = {
                "score": score_planning_signal(case, raw_planning.get("signal") or {}),
                "signal": raw_planning.get("signal") or {},
                "usage_events": list(raw_planning.get("usage_events") or ()),
            }
        result["hard_failures"] = _detect_hard_failures(case, result)
        results.append(result)

    report = _report(results)
    provenance = dict(acquisition.get("provenance") or {})
    report["provenance"] = {
        "scored_from_acquisition_id": str(acquisition.get("acquisition_id") or ""),
        "acquisition_content_sha256": str(acquisition.get("content_sha256") or ""),
        "acquisition_git_commit_sha": provenance.get("git_commit_sha"),
        "acquisition_corpus_sha256": provenance.get("corpus_sha256"),
        "oracle_source": oracle_source,
        "scoring_corpus_sha256": (
            provenance.get("corpus_sha256") if oracle_source == "captured" else current_oracle_sha256
        ),
        "scoring_git_commit_sha": (
            provenance.get("git_commit_sha") if oracle_source == "captured" else current_oracle_git_sha
        ),
    }
    return report


def _load_acquisitions(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    kind = str(payload.get("kind") or "") if isinstance(payload, Mapping) else ""
    if kind == "analytical_eval_acquisition":
        _verify_sealed_payload(payload)
        return [dict(payload)]
    if kind == "analytical_eval_acquisition_set":
        _verify_sealed_payload(payload)
        acquisitions = [dict(value) for value in (payload.get("acquisitions") or ())]
        for acquisition in acquisitions:
            _verify_sealed_payload(acquisition)
        return acquisitions
    raise ValueError(f"unsupported analytical acquisition payload in {path}")


def _stability_report(
    acquisitions: Sequence[Mapping[str, Any]],
    reports: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(acquisitions) != len(reports) or len(acquisitions) < 2:
        raise ValueError("stability analysis requires matching acquisition/report sequences of length >= 2")
    case_orders = [tuple(str(row.get("case_id")) for row in acq.get("cases") or ()) for acq in acquisitions]
    if any(order != case_orders[0] for order in case_orders[1:]):
        raise ValueError("stability comparison requires identical case IDs in identical order")

    report_rows = [
        {str(row["case_id"]): row for row in report.get("results") or ()}
        for report in reports
    ]
    acquisition_rows = [
        {str(row["case_id"]): row for row in acquisition.get("cases") or ()}
        for acquisition in acquisitions
    ]
    metric_extractors = {
        "reasoning_pass": lambda raw, scored: (scored.get("reasoning") or {}).get("score", {}).get("pass"),
        "reasoning_complete": lambda raw, scored: (scored.get("reasoning") or {}).get("score", {}).get("complete"),
        "planning_pass": lambda raw, scored: (scored.get("planning") or {}).get("score", {}).get("pass"),
        "interpreted_intent": lambda raw, scored: (raw.get("current") or {}).get("interpreted_intent"),
        "legacy_target": lambda raw, scored: (raw.get("current") or {}).get("target_move"),
        "validator_signature": lambda raw, scored: _validator_signature(raw),
        "planner_status": lambda raw, scored: _planner_status(raw),
        "primary_need": lambda raw, scored: _planning_signal_value(raw, "primary_need"),
        "primary_need_source": lambda raw, scored: _planning_signal_value(raw, "primary_need_source"),
        "semantic_primary_need": lambda raw, scored: _planning_signal_value(raw, "semantic_primary_need"),
        "planning_path": lambda raw, scored: _planning_path_signature(raw),
        "selected_move": lambda raw, scored: _shadow_value(raw, "selected_move_type"),
        "selected_target": lambda raw, scored: _shadow_value(raw, "target_outcome"),
        "realization_repair": lambda raw, scored: _realization_repair_signature(raw),
        "realized_question_valid": lambda raw, scored: (scored.get("planning") or {}).get("score", {}).get("question_ok"),
        "hard_failures": lambda raw, scored: tuple(scored.get("hard_failures") or ()),
    }
    metric_summaries: dict[str, Any] = {}
    per_case: list[dict[str, Any]] = []
    for case_id in case_orders[0]:
        case_metrics: dict[str, Any] = {"case_id": case_id, "metrics": {}}
        for metric, extractor in metric_extractors.items():
            values = [
                extractor(acquisition_rows[i][case_id], report_rows[i][case_id])
                for i in range(len(acquisitions))
            ]
            normalized = [_stable_json_value(value) for value in values]
            counts = Counter(normalized)
            case_metrics["metrics"][metric] = {
                "stable": len(counts) == 1,
                "majority_count": max(counts.values()),
                "majority_rate": round(max(counts.values()) / len(values), 4),
                "distribution": dict(sorted(counts.items())),
            }
        per_case.append(case_metrics)

    for metric in metric_extractors:
        rows = [row["metrics"][metric] for row in per_case]
        stable_count = sum(bool(row["stable"]) for row in rows)
        metric_summaries[metric] = {
            "stable_case_count": stable_count,
            "changed_case_count": len(rows) - stable_count,
            "stability_rate": _rate(stable_count, len(rows)),
            "mean_majority_rate": round(sum(float(row["majority_rate"]) for row in rows) / len(rows), 4) if rows else None,
        }

    costs = [float((report.get("summary") or {}).get("estimated_cost_usd") or 0) for report in reports]
    return {
        "schema_version": 1,
        "kind": "analytical_eval_stability_report",
        "acquisition_count": len(acquisitions),
        "case_count": len(case_orders[0]),
        "acquisition_ids": [str(acq.get("acquisition_id") or "") for acq in acquisitions],
        "acquisition_git_commits": [str((acq.get("provenance") or {}).get("git_commit_sha") or "") for acq in acquisitions],
        "acquisition_corpus_sha256": [str((acq.get("provenance") or {}).get("corpus_sha256") or "") for acq in acquisitions],
        "models_by_purpose": [dict((acq.get("provenance") or {}).get("models_by_purpose") or {}) for acq in acquisitions],
        "scoring_oracle_sources": [str((report.get("provenance") or {}).get("oracle_source") or "") for report in reports],
        "scoring_corpus_sha256": [str((report.get("provenance") or {}).get("scoring_corpus_sha256") or "") for report in reports],
        "scoring_oracle_consistent": len({
            (
                str((report.get("provenance") or {}).get("oracle_source") or ""),
                str((report.get("provenance") or {}).get("scoring_corpus_sha256") or ""),
            )
            for report in reports
        }) == 1,
        "metrics": metric_summaries,
        "cost_usd": {
            "values": costs,
            "min": min(costs) if costs else None,
            "max": max(costs) if costs else None,
            "mean": round(sum(costs) / len(costs), 6) if costs else None,
            "max_to_min_ratio": round(max(costs) / min(costs), 3) if costs and min(costs) > 0 else None,
        },
        "cases": per_case,
    }


def _validator_signature(raw: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    signal = (raw.get("reasoning") or {}).get("signal") or {}
    return tuple(sorted(
        (str(item.get("dimension") or ""), str(item.get("decision") or ""))
        for item in (signal.get("evaluations") or ())
        if isinstance(item, Mapping)
    ))


def _planner_status(raw: Mapping[str, Any]) -> tuple[str, str, str]:
    signal = (raw.get("planning") or {}).get("signal") or {}
    return (
        str(signal.get("status") or ""),
        str(signal.get("failure_stage") or ""),
        str(signal.get("error_type") or ""),
    )


def _shadow_value(raw: Mapping[str, Any], key: str) -> str:
    signal = (raw.get("planning") or {}).get("signal") or {}
    return str((signal.get("shadow_planner") or {}).get(key) or "")


def _planning_signal_value(raw: Mapping[str, Any], key: str) -> str:
    signal = (raw.get("planning") or {}).get("signal") or {}
    shadow = signal.get("shadow_planner") or {}
    return str(shadow.get(key) or signal.get(key) or "")


def _planning_path_signature(raw: Mapping[str, Any]) -> tuple[str, str, str]:
    signal = (raw.get("planning") or {}).get("signal") or {}
    shadow = signal.get("shadow_planner") or {}
    return (
        str(shadow.get("primary_need") or signal.get("primary_need") or ""),
        str(shadow.get("selected_move_type") or ""),
        str(shadow.get("target_outcome") or ""),
    )


def _realization_repair_signature(raw: Mapping[str, Any]) -> tuple[bool, bool, tuple[str, ...], tuple[str, ...]]:
    signal = (raw.get("planning") or {}).get("signal") or {}
    shadow = signal.get("shadow_planner") or {}
    repair = shadow.get("realization_repair") or signal.get("realization_repair") or {}
    return (
        bool(repair.get("attempted")),
        bool(repair.get("succeeded")),
        tuple(str(item) for item in (repair.get("initial_rejection_codes") or ())),
        tuple(str(item) for item in (repair.get("final_rejection_codes") or ())),
    )


def _stable_json_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _models_by_purpose(records: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for row in records:
        for family in ("current", "reasoning", "planning"):
            for event in (row.get(family) or {}).get("usage_events") or ():
                model = str(event.get("model") or "").strip()
                if model:
                    found[str(event.get("purpose") or family)].add(model)
    return {purpose: sorted(models) for purpose, models in sorted(found.items())}


def _new_acquisition_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"AE-{stamp}-{uuid.uuid4().hex[:8]}"


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _payload_digest(payload: Mapping[str, Any]) -> str:
    body = {str(k): v for k, v in payload.items() if k != "content_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _seal_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["content_sha256"] = _payload_digest(result)
    return result


def _verify_sealed_payload(payload: Mapping[str, Any]) -> None:
    expected = str(payload.get("content_sha256") or "")
    if not expected or expected != _payload_digest(payload):
        raise ValueError("analytical acquisition content hash mismatch")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _print_stability(stability: Mapping[str, Any]) -> None:
    print("\nAnalytical evaluation stability")
    print("  acquisitions:", stability.get("acquisition_count"))
    print("  cases:", stability.get("case_count"))
    metrics = dict(stability.get("metrics") or {})
    for name in (
        "reasoning_pass",
        "reasoning_complete",
        "planning_pass",
        "interpreted_intent",
        "legacy_target",
        "validator_signature",
        "planner_status",
        "primary_need",
        "primary_need_source",
        "semantic_primary_need",
        "planning_path",
        "selected_move",
        "selected_target",
        "realization_repair",
        "realized_question_valid",
        "hard_failures",
    ):
        values = dict(metrics.get(name) or {})
        print(
            f"  {name}: stability={values.get('stability_rate')} "
            f"changed={values.get('changed_case_count')}"
        )
    print("  scoring oracle consistent:", stability.get("scoring_oracle_consistent"))
    print("  cost USD:", (stability.get("cost_usd") or {}).get("values"))


def _report_passes(report: Mapping[str, Any]) -> bool:
    thresholds = json.loads(RUBRIC_PATH.read_text())["machine_acceptance"]
    hard_count = report["summary"]["hard_failure_count"]
    reasoning_rate = report["summary"].get("reasoning_pass_rate")
    planning_rate = report["summary"].get("planning_move_pass_rate")
    question_rate = report["summary"].get("realized_question_valid_rate")
    reasoning_ok = reasoning_rate is None or _meets_thresholds(
        reasoning_rate,
        report["by_phase"],
        "reasoning_pass_rate",
        thresholds["reasoning_oracle_overall_min"],
        thresholds["reasoning_oracle_each_phase_min"],
    )
    planning_ok = planning_rate is None or _meets_thresholds(
        planning_rate,
        report["by_phase"],
        "planning_move_pass_rate",
        thresholds["planner_acceptable_move_overall_min"],
        thresholds["planner_acceptable_move_each_phase_min"],
    )
    question_ok = question_rate is None or (
        float(question_rate) >= float(thresholds["realized_question_machine_valid_min"])
    )
    return bool(
        hard_count <= thresholds["hard_failure_count_max"]
        and reasoning_ok
        and planning_ok
        and question_ok
    )

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
        "interpreted_intent": str(reviewer.get("interpreted_intent") or "other"),
        "teach_back": bool(reviewer.get("teach_back", False)),
        "kind": str(reviewer.get("kind") or "conversation"),
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
        "signal": outcome.signal,
        "usage_events": list(outcome.usage_events),
    }


def _run_planning_case(
    planner: ReviewPlanner, case: Mapping[str, Any], current_engine: Mapping[str, Any]
) -> dict[str, Any]:
    outcome = planner.plan_turn(
        context=build_planning_context(case, current_engine=current_engine),
        shadow_state=blank_planning_shadow(),
        current_engine=dict(current_engine),
        turn_sequence=1,
        client_turn_id=f"eval-{case['id']}",
        operation="respond",
    )
    return {
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
    if _mentions_hidden_grading(lower):
        failures.append("HIDDEN_GRADING_BEHAVIOR")
    if any(term in lower for term in ("chain of thought", "system prompt", "hidden reasoning")):
        failures.append("CHAIN_OF_THOUGHT_EXPOSURE")
    if "correct_student_challenge" in set(case.get("tags") or ()) and not _addresses_correct_student_challenge(
        move, str(shadow.get("target_outcome") or "")
    ):
        failures.append("IGNORES_CORRECT_STUDENT_CHALLENGE")
    if "legitimate_unknown" in set(case.get("tags") or ()) and move in {"SYNTHESIZE_OBJECTIVE"}:
        failures.append("FALSE_CERTAINTY_FROM_LEGITIMATE_UNKNOWN")
    return sorted(set(failures))


def _addresses_correct_student_challenge(move: str, target: str) -> bool:
    """Return whether the selected move actually stays on the evidence-backed dispute.

    The hard-failure detector must evaluate the semantic move/target pair rather
    than the move label alone. TEST_EVIDENCE_BOUNDARY against FINDING_EVIDENCE_TESTED
    directly tests the disputed finding evidence and therefore does not ignore a
    correct student challenge. Downstream action/change moves still fail this guard.
    """
    if move in {
        "ADDRESS_STUDENT_CHALLENGE",
        "TEST_FINDING_SUPPORT",
        "RECONCILE_CONTRADICTION",
    }:
        return True
    return move == "TEST_EVIDENCE_BOUNDARY" and target == "FINDING_EVIDENCE_TESTED"


def _mentions_hidden_grading(text: str) -> bool:
    if re.search(r"\b(?:full credit|rubric score)\b", text):
        return True
    # Bare engineering uses of "point" are common (approval point, decision point,
    # failure point). Treat points as grading only when the surrounding language
    # makes an academic scoring meaning explicit.
    if re.search(
        r"\b(?:earn|earns|earning|award|awards|awarded|receive|receives|received|"
        r"lose|loses|lost|deduct|deducts|deducted|worth)\s+(?:\d+(?:\.\d+)?\s+)?points?\b",
        text,
    ):
        return True
    if re.search(
        r"\bpoints?\s+(?:on|for|toward|towards)\s+(?:the\s+)?(?:grade|rubric|assignment|score)\b",
        text,
    ):
        return True
    # Avoid false positives for ordinary engineering adjectives such as
    # "enterprise-grade" while still catching direct grading language.
    return bool(re.search(r"(?<![-\w])grad(?:e|ed|es|ing)(?![-\w])", text))


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
    reasoning_judgment_count = sum(
        int(row["reasoning"]["score"].get("requested_dimension_count") or 0)
        for row in reasoning_rows
    )
    reasoning_missing_result_count = sum(
        int(row["reasoning"]["score"].get("missing_result_count") or 0)
        for row in reasoning_rows
    )
    summary["reasoning_dimension_judgment_count"] = reasoning_judgment_count
    summary["reasoning_missing_result_count"] = reasoning_missing_result_count
    summary["reasoning_validator_completeness_rate"] = _rate(
        reasoning_judgment_count - reasoning_missing_result_count,
        reasoning_judgment_count,
    )
    summary["reasoning_complete_case_count"] = sum(
        bool(row["reasoning"]["score"].get("complete")) for row in reasoning_rows
    )
    summary["reasoning_complete_case_rate"] = _rate(
        summary["reasoning_complete_case_count"],
        len(reasoning_rows),
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
    path_rows = [
        row for row in planning_rows
        if bool(row["planning"]["score"].get("path_contract_active"))
    ]
    summary["planning_path_contract_case_count"] = len(path_rows)
    summary["planning_path_pass_rate"] = _rate(
        sum(bool(row["planning"]["score"].get("path_pass")) for row in path_rows),
        len(path_rows),
    )
    summary["planning_preferred_path_match_rate"] = _rate(
        sum(bool(row["planning"]["score"].get("preferred_path_match")) for row in path_rows),
        len(path_rows),
    )
    summary["realized_question_valid_rate"] = _rate(
        sum(bool(row["planning"]["score"]["question_ok"]) for row in planning_rows), len(planning_rows)
    )

    by_phase: dict[str, dict[str, Any]] = {}
    for phase in [f"A{i}" for i in range(1, 7)]:
        phase_rows = [row for row in results if row["phase_id"] == phase]
        r_rows = [row for row in phase_rows if "reasoning" in row]
        p_rows = [row for row in phase_rows if "planning" in row]
        phase_reasoning_judgment_count = sum(
            int(row["reasoning"]["score"].get("requested_dimension_count") or 0)
            for row in r_rows
        )
        phase_reasoning_missing_result_count = sum(
            int(row["reasoning"]["score"].get("missing_result_count") or 0)
            for row in r_rows
        )
        phase_reasoning_complete_case_count = sum(
            bool(row["reasoning"]["score"].get("complete")) for row in r_rows
        )
        by_phase[phase] = {
            "case_count": len(phase_rows),
            "reasoning_pass_rate": _rate(sum(bool(row["reasoning"]["score"]["pass"]) for row in r_rows), len(r_rows)),
            "reasoning_dimension_judgment_count": phase_reasoning_judgment_count,
            "reasoning_missing_result_count": phase_reasoning_missing_result_count,
            "reasoning_validator_completeness_rate": _rate(
                phase_reasoning_judgment_count - phase_reasoning_missing_result_count,
                phase_reasoning_judgment_count,
            ),
            "reasoning_complete_case_count": phase_reasoning_complete_case_count,
            "reasoning_complete_case_rate": _rate(phase_reasoning_complete_case_count, len(r_rows)),
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
            "planning_path_contract_case_count": len([
                row for row in p_rows
                if bool(row["planning"]["score"].get("path_contract_active"))
            ]),
            "planning_path_pass_rate": _rate(
                sum(
                    bool(row["planning"]["score"].get("path_pass"))
                    for row in p_rows
                    if bool(row["planning"]["score"].get("path_contract_active"))
                ),
                len([
                    row for row in p_rows
                    if bool(row["planning"]["score"].get("path_contract_active"))
                ]),
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
    return {"schema_version": REPORT_SCHEMA_VERSION, "summary": summary, "by_phase": by_phase, "results": results}


def _print_summary(report: Mapping[str, Any]) -> None:
    summary = report["summary"]
    print("\nAnalytical engine evaluation summary")
    print("  cases:", summary["case_count"])
    print("  reasoning pass rate:", summary.get("reasoning_pass_rate"))
    print("  reasoning validator completeness rate:", summary.get("reasoning_validator_completeness_rate"))
    print("  reasoning missing results:", summary.get("reasoning_missing_result_count"))
    print("  planning pass rate:", summary.get("planning_pass_rate"))
    print("  planning move pass rate:", summary.get("planning_move_pass_rate"))
    print("  explicit move oracle match rate:", summary.get("planning_explicit_move_match_rate"))
    print("  preferred move match rate:", summary.get("planning_preferred_move_match_rate"))
    print("  planning path contract cases:", summary.get("planning_path_contract_case_count"))
    print("  planning path pass rate:", summary.get("planning_path_pass_rate"))
    print("  preferred path match rate:", summary.get("planning_preferred_path_match_rate"))
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
