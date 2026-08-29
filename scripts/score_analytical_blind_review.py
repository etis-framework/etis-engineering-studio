#!/usr/bin/env python3
"""Score blinded current-vs-shadow human review packets for ETIS v0.17."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
RUBRIC_PATH = ROOT / "evals" / "analytical_engine_rubric.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score one or more completed ETIS blind-review packets.")
    parser.add_argument("--packet", type=Path, action="append", required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def score_packets(packet_paths: list[Path], key_path: Path) -> dict[str, Any]:
    resolved_packets = [path.resolve() for path in packet_paths]
    if len(resolved_packets) != len(set(resolved_packets)):
        raise ValueError("the same blind-review packet path cannot be counted more than once")
    rubric = json.loads(RUBRIC_PATH.read_text())
    allowed_hard_failures = set(rubric["hard_failures"])
    allowed_dimensions = {str(row["id"]) for row in rubric["human_dimensions"]}

    key_rows = json.loads(key_path.read_text())
    key = {
        str(row["review_id"]): {
            "case_id": str(row["case_id"]),
            "current_source": str(row.get("current_source") or "unknown"),
            "A": row["A"],
            "B": row["B"],
        }
        for row in key_rows
    }
    preference = Counter()
    hard_failures: dict[str, Counter[str]] = {
        "current": Counter(),
        "shadow": Counter(),
    }
    case_ratings = Counter()
    dimension_totals: dict[str, dict[str, list[float]]] = {
        "current": defaultdict(list),
        "shadow": defaultdict(list),
    }
    ratings = 0

    for path in packet_paths:
        rows = json.loads(path.read_text())
        seen_in_packet: set[str] = set()
        for row in rows:
            review_id = str(row.get("review_id") or "")
            if review_id not in key:
                raise ValueError(f"packet {path} contains review not present in key: {review_id}")
            if review_id in seen_in_packet:
                raise ValueError(f"packet {path} contains duplicate review rating: {review_id}")
            seen_in_packet.add(review_id)
            case_id = str(key[review_id]["case_id"])

            raw_pref = str(row.get("preference") or "").strip().upper()
            if raw_pref not in {"A", "B", "TIE"}:
                continue

            ratings += 1
            case_ratings[case_id] += 1
            if raw_pref == "TIE":
                preference["tie"] += 1
            else:
                preference[key[review_id][raw_pref]] += 1

            raw_hard = row.get("hard_failures") or {}
            if not isinstance(raw_hard, Mapping):
                raise ValueError(f"packet {path} case {case_id} hard_failures must be an object")
            for label in ("A", "B"):
                source = str(key[review_id][label])
                for value in _hard_failure_values(raw_hard.get(label)):
                    if value not in allowed_hard_failures:
                        raise ValueError(
                            f"packet {path} case {case_id} contains unknown hard failure {value!r}"
                        )
                    hard_failures[source][value] += 1

            raw_scores = row.get("dimension_scores") or {}
            if not isinstance(raw_scores, Mapping):
                raise ValueError(f"packet {path} case {case_id} dimension_scores must be an object")
            for label in ("A", "B"):
                source = str(key[review_id][label])
                label_scores = raw_scores.get(label) or {}
                if not isinstance(label_scores, Mapping):
                    raise ValueError(
                        f"packet {path} case {case_id} dimension_scores[{label}] must be an object"
                    )
                for dimension, value in label_scores.items():
                    dimension = str(dimension)
                    if dimension not in allowed_dimensions:
                        raise ValueError(
                            f"packet {path} case {case_id} contains unknown dimension {dimension!r}"
                        )
                    if value in (None, ""):
                        continue
                    try:
                        score = float(value)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            f"packet {path} case {case_id} dimension {dimension} is not numeric"
                        ) from exc
                    if not 0 <= score <= 2:
                        raise ValueError(
                            f"packet {path} case {case_id} dimension {dimension} must be between 0 and 2"
                        )
                    dimension_totals[source][dimension].append(score)

    def rate(name: str) -> float:
        return round(preference[name] / ratings, 4) if ratings else 0.0

    expected_case_ids = sorted({str(value["case_id"]) for value in key.values()})
    ratings_per_case = {case_id: int(case_ratings.get(case_id, 0)) for case_id in expected_case_ids}
    current_source_counts = Counter(str(value["current_source"]) for value in key.values())
    result = {
        "schema_version": 1,
        "current_question_sources": dict(current_source_counts),
        "ratings": ratings,
        "distinct_cases": sum(1 for value in ratings_per_case.values() if value > 0),
        "ratings_per_case": ratings_per_case,
        "minimum_ratings_observed_per_case": min(ratings_per_case.values()) if ratings_per_case else 0,
        "preferences": {
            "shadow": preference["shadow"],
            "current": preference["current"],
            "tie": preference["tie"],
            "shadow_rate": rate("shadow"),
            "current_rate": rate("current"),
            "tie_rate": rate("tie"),
            "shadow_or_tie_rate": round(
                (preference["shadow"] + preference["tie"]) / ratings, 4
            ) if ratings else 0.0,
        },
        "hard_failures": {
            source: dict(values) for source, values in hard_failures.items()
        },
        "hard_failure_counts": {
            source: sum(values.values()) for source, values in hard_failures.items()
        },
        "dimension_means": {
            source: {
                dimension: round(sum(values) / len(values), 3)
                for dimension, values in dimensions.items()
                if values
            }
            for source, dimensions in dimension_totals.items()
        },
    }
    result["acceptance"] = evaluate_acceptance(result)
    return result


def _hard_failure_values(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple, set)):
        return tuple(str(part).strip() for part in value if str(part).strip())
    raise ValueError("hard failure values must be a string or list")


def evaluate_acceptance(result: dict[str, Any]) -> dict[str, Any]:
    thresholds = json.loads(RUBRIC_PATH.read_text())["blind_human_acceptance"]
    prefs = result["preferences"]
    checks = {
        "minimum_ratings": result["ratings"] >= thresholds["minimum_ratings"],
        "minimum_distinct_cases": result["distinct_cases"] >= thresholds["minimum_distinct_cases"],
        "minimum_raters_per_case": (
            result["minimum_ratings_observed_per_case"] >= thresholds["minimum_raters_per_case"]
        ),
        "shadow_preferred": prefs["shadow_rate"] >= thresholds["shadow_preferred_min"],
        "current_preferred": prefs["current_rate"] <= thresholds["current_preferred_max"],
        "shadow_preferred_or_tie": (
            prefs["shadow_or_tie_rate"] >= thresholds["shadow_preferred_or_tie_min"]
        ),
        "shadow_hard_failures": (
            result["hard_failure_counts"]["shadow"] <= thresholds["hard_failure_count_max"]
        ),
        "live_current_engine_only": (
            not thresholds.get("require_live_current_engine", False)
            or set(result.get("current_question_sources") or {}) <= {"live_current_engine"}
        ),
    }
    return {"pass": all(checks.values()), "checks": checks}


def main() -> int:
    args = parse_args()
    result = score_packets(args.packet, args.key)
    print(json.dumps(result, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["acceptance"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
