from __future__ import annotations

from collections import Counter

from apps.api.app.services.next_question_selector import NextQuestionSelector
from apps.api.app.services.review_planning import CandidateRejectionCode
from scripts.analytical_eval_support import (
    build_objective,
    build_planning_context,
    load_cases,
    oracle_candidates,
    reasoning_probe,
    validate_enum_contract,
)


REQUIRED_BEHAVIOR_TAGS = {
    "excellent_evidence",
    "weak_evidence_polished_prose",
    "blind_ai_agreement",
    "reflexive_ai_rejection",
    "correct_student_challenge",
    "strong_code_weak_architecture",
    "strong_docs_weak_implementation",
    "ai_generated_code_without_understanding",
    "verbose_vagueness",
    "architecture_change",
    "contradiction",
    "stale_evidence",
    "legitimate_unknown",
    "uneven_team_understanding",
}


def test_analytical_eval_corpus_has_balanced_a1_a6_coverage():
    rows = load_cases()
    assert len(rows) >= 42
    phase_counts = Counter(row["phase_id"] for row in rows)
    assert phase_counts == {f"A{i}": 7 for i in range(1, 7)}


def test_analytical_eval_corpus_has_required_behavior_wargames_and_modes():
    rows = load_cases()
    tags = {tag for row in rows for tag in row.get("tags", [])}
    assert REQUIRED_BEHAVIOR_TAGS.issubset(tags)
    modes = {row["review_mode"] for row in rows}
    assert modes == {"board_review", "focused_review", "finding_review"}
    assert sum(row["review_mode"] == "finding_review" for row in rows) >= 6
    for phase in [f"A{i}" for i in range(1, 7)]:
        phase_modes = {row["review_mode"] for row in rows if row["phase_id"] == phase}
        assert phase_modes == {"board_review", "focused_review", "finding_review"}, phase


def test_analytical_eval_case_ids_are_unique_and_contracts_are_valid():
    rows = load_cases()
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    for row in rows:
        validate_enum_contract(row)
        objective = build_objective(row)
        assert objective.phase_id == row["phase_id"]
        assert objective.review_mode.value == row["review_mode"]
        assert objective.objective_id == f"eval-{row['id']}"
        assert objective.evidence_refs
        expectations = row["expectations"]
        assert expectations["acceptable_moves"]
        assert expectations["preferred_moves"]
        assert expectations["acceptable_target_outcomes"]
        assert expectations["preferred_moves"][0] in expectations["acceptable_moves"]
        assert not set(expectations["preferred_moves"]) & set(expectations["forbidden_moves"])


def test_every_case_has_a_reasoning_probe_with_explicit_oracle():
    for row in load_cases():
        proposals, expected = reasoning_probe(row)
        assert proposals, row["id"]
        assert expected, row["id"]
        assert set(expected) == set(proposals), row["id"]
        assert all(values for values in expected.values()), row["id"]


def test_selector_oracle_prefers_expected_move_for_every_wargame():
    selector = NextQuestionSelector()
    for row in load_cases():
        context = build_planning_context(row)
        selected, rejected = selector.select(
            context=context,
            candidates=oracle_candidates(row),
        )
        assert selected is not None, row["id"]
        assert selected.selected_move_type.value == row["expectations"]["preferred_moves"][0], row["id"]
        assert selected.target_outcome.value in row["expectations"]["acceptable_target_outcomes"], row["id"]
        rejected_by_id = {item.candidate_id: item for item in rejected}
        assert "invalid-ref" in rejected_by_id, row["id"]
        assert (
            CandidateRejectionCode.NO_FROZEN_EVIDENCE_BASIS
            in rejected_by_id["invalid-ref"].rejection_codes
        ), row["id"]


def test_teaching_wargames_force_teaching_candidate_in_selector_oracle():
    selector = NextQuestionSelector()
    teaching_rows = [row for row in load_cases() if row["expectations"]["requires_teaching"]]
    assert len(teaching_rows) >= 6
    for row in teaching_rows:
        selected, _ = selector.select(
            context=build_planning_context(row),
            candidates=oracle_candidates(row),
        )
        assert selected is not None, row["id"]
        assert selected.teaching_required is True, row["id"]


def test_finding_review_wargames_preserve_student_challenge_and_supported_findings():
    rows = [row for row in load_cases() if row["review_mode"] == "finding_review"]
    assert rows
    assert any("finding_supported" in row["tags"] for row in rows)
    for row in rows:
        objective = build_objective(row)
        assert objective.subject.subject_type.value == "finding"
        if "correct_student_challenge" in row["tags"]:
            assert "ADDRESS_STUDENT_CHALLENGE" in row["expectations"]["acceptable_moves"]
            assert row["context"]["evidence_disputes"]


def test_legitimate_unknown_cases_do_not_force_false_closure():
    rows = [row for row in load_cases() if "legitimate_unknown" in row["tags"]]
    assert len(rows) >= 5
    for row in rows:
        moves = set(row["expectations"]["acceptable_moves"])
        targets = set(row["expectations"]["acceptable_target_outcomes"])
        assert moves & {"SURFACE_UNCERTAINTY", "REQUEST_MISSING_EVIDENCE", "ESTABLISH_CHANGE_TRIGGER"}
        assert targets & {
            "UNCERTAINTY_CLEAR",
            "NEXT_IMPROVEMENT_OR_EVIDENCE_NEED_CLEAR",
            "CHANGE_OR_CLOSURE_CONDITION_CLEAR",
        }
        assert row["context"]["explicit_uncertainty"]


def test_corpus_does_not_use_future_phase_as_expected_move():
    for row in load_cases():
        title = row["scenario"]["title"].lower()
        statement = row["scenario"]["statement"].lower()
        # Cases may explicitly test the future-phase guard, but their oracle must
        # remain current-phase and never require future implementation evidence.
        if "future_phase_guard" in row["tags"]:
            assert row["phase_id"] == "A3"
        assert "A7" not in title + statement


def test_analytical_eval_rubric_has_hard_authority_gates_and_enablement_thresholds():
    import json
    from pathlib import Path

    rubric = json.loads(Path("evals/analytical_engine_rubric.json").read_text())
    hard = set(rubric["hard_failures"])
    assert {
        "FABRICATED_EVIDENCE",
        "UNAUTHORIZED_EVIDENCE_REFERENCE",
        "FUTURE_PHASE_DEMAND",
        "HIDDEN_GRADING_BEHAVIOR",
        "IGNORES_CORRECT_STUDENT_CHALLENGE",
        "FALSE_CERTAINTY_FROM_LEGITIMATE_UNKNOWN",
    }.issubset(hard)
    machine = rubric["machine_acceptance"]
    assert machine["reasoning_oracle_overall_min"] >= 0.90
    assert machine["planner_acceptable_move_overall_min"] >= 0.90
    assert machine["hard_failure_count_max"] == 0
    human = rubric["blind_human_acceptance"]
    assert human["minimum_distinct_cases"] >= 42
    assert human["minimum_raters_per_case"] >= 2
    assert human["hard_failure_count_max"] == 0
    assert human["require_live_current_engine"] is True


def test_blind_review_scorer_maps_randomized_labels_and_scores_each_source(tmp_path):
    import json
    from scripts.score_analytical_blind_review import score_packets

    key = [
        {"review_id": "R001", "case_id": "c1", "current_source": "live_current_engine", "A": "shadow", "B": "current"},
        {"review_id": "R002", "case_id": "c2", "current_source": "live_current_engine", "A": "current", "B": "shadow"},
    ]
    packet = [
        {
            "review_id": "R001",
            "preference": "A",
            "hard_failures": {"A": [], "B": ["OBJECTIVE_ESCAPE"]},
            "dimension_scores": {
                "A": {"overall_next_move": 2},
                "B": {"overall_next_move": 0},
            },
        },
        {
            "review_id": "R002",
            "preference": "B",
            "hard_failures": {"A": [], "B": []},
            "dimension_scores": {
                "A": {"overall_next_move": 1},
                "B": {"overall_next_move": 2},
            },
        },
    ]
    key_path = tmp_path / "key.json"
    packet_path = tmp_path / "packet.json"
    key_path.write_text(json.dumps(key))
    packet_path.write_text(json.dumps(packet))

    result = score_packets([packet_path], key_path)

    assert result["ratings"] == 2
    assert result["preferences"]["shadow"] == 2
    assert result["preferences"]["current"] == 0
    assert result["preferences"]["shadow_rate"] == 1.0
    assert result["dimension_means"]["shadow"]["overall_next_move"] == 2.0
    assert result["dimension_means"]["current"]["overall_next_move"] == 0.5
    assert result["hard_failure_counts"]["shadow"] == 0
    assert result["hard_failure_counts"]["current"] == 1
    assert result["acceptance"]["checks"]["minimum_raters_per_case"] is False
    assert result["acceptance"]["checks"]["shadow_hard_failures"] is True
    assert result["acceptance"]["checks"]["live_current_engine_only"] is True


def test_blind_review_scorer_enforces_two_completed_ratings_per_case(tmp_path):
    import json
    from scripts.score_analytical_blind_review import score_packets

    key = [{"review_id": "R001", "case_id": "c1", "current_source": "live_current_engine", "A": "current", "B": "shadow"}]
    one_rating = [{
        "review_id": "R001",
        "preference": "B",
        "hard_failures": {"A": [], "B": []},
        "dimension_scores": {"A": {}, "B": {}},
    }]
    key_path = tmp_path / "key.json"
    first = tmp_path / "rater1.json"
    second = tmp_path / "rater2.json"
    key_path.write_text(json.dumps(key))
    first.write_text(json.dumps(one_rating))
    second.write_text(json.dumps(one_rating))

    first_result = score_packets([first], key_path)
    assert first_result["minimum_ratings_observed_per_case"] == 1
    assert first_result["acceptance"]["checks"]["minimum_raters_per_case"] is False

    two_result = score_packets([first, second], key_path)
    assert two_result["minimum_ratings_observed_per_case"] == 2
    assert two_result["acceptance"]["checks"]["minimum_raters_per_case"] is True


def test_blind_packet_hides_oracle_labels_and_includes_decision_context(tmp_path):
    import json
    from scripts.run_analytical_engine_evals import _write_blind_packet

    case = next(row for row in load_cases() if "correct_student_challenge" in row["tags"])
    result = {
        "case_id": case["id"],
        "phase_id": case["phase_id"],
        "review_mode": case["review_mode"],
        "tags": case["tags"],
        "current": {"source": "live_current_engine"},
        "legacy_question": "What evidence supports your disagreement?",
        "planning": {
            "signal": {
                "shadow_planner": {
                    "proposed_question": "Which frozen evidence would show that the finding should be corrected?"
                }
            }
        },
    }
    packet_path = tmp_path / "packet.json"
    key_path = tmp_path / "key.json"
    _write_blind_packet([result], {case["id"]: case}, packet_path, key_path, 33017)

    packet = json.loads(packet_path.read_text())
    key = json.loads(key_path.read_text())
    assert len(packet) == len(key) == 1
    row = packet[0]
    assert row["review_id"] == "R001"
    assert "case_id" not in row
    assert "tags" not in row
    assert row["case_context"]["review_objective"]
    assert row["case_context"]["frozen_evidence"]
    assert row["case_context"]["student"]["turn"]
    assert row["case_context"]["evidence_disputes"]
    assert set(row["dimension_scores"]) == {"A", "B"}
    assert key[0]["case_id"] == case["id"]
    assert key[0]["current_source"] == "live_current_engine"
    assert {key[0]["A"], key[0]["B"]} == {"current", "shadow"}


def test_live_hard_failure_scan_uses_full_selector_evidence_authority():
    from scripts.run_analytical_engine_evals import _detect_hard_failures

    case = dict(load_cases()[0])
    case["challenge"] = dict(case["challenge"])
    case["challenge"]["evidence_refs"] = []
    case["evidence_package"] = dict(case["evidence_package"])
    case["evidence_package"]["relevant_items"] = [
        {"ref": "PATH:authorized-via-package.md", "title": "authorized-via-package.md"}
    ]
    result = {
        "planning": {
            "signal": {
                "shadow_planner": {
                    "selected_move_type": "TEST_EVIDENCE_BOUNDARY",
                    "proposed_question": "What does the authorized evidence establish?",
                    "evidence_refs": ["PATH:authorized-via-package.md"],
                }
            }
        }
    }
    assert "UNAUTHORIZED_EVIDENCE_REFERENCE" not in _detect_hard_failures(case, result)


def test_blind_human_gate_rejects_fixture_current_questions(tmp_path):
    import json
    from scripts.score_analytical_blind_review import score_packets

    key = [{
        "review_id": "R001",
        "case_id": "c1",
        "current_source": "fixture",
        "A": "current",
        "B": "shadow",
    }]
    packet = [{
        "review_id": "R001",
        "preference": "B",
        "hard_failures": {"A": [], "B": []},
        "dimension_scores": {"A": {}, "B": {}},
    }]
    key_path = tmp_path / "key.json"
    packet_path = tmp_path / "packet.json"
    key_path.write_text(json.dumps(key))
    packet_path.write_text(json.dumps(packet))

    result = score_packets([packet_path], key_path)
    assert result["current_question_sources"] == {"fixture": 1}
    assert result["acceptance"]["checks"]["live_current_engine_only"] is False


def test_machine_report_separates_move_quality_realization_and_usage_cost():
    from scripts.run_analytical_engine_evals import _report

    report = _report([
        {
            "case_id": "c1",
            "phase_id": "A1",
            "review_mode": "board_review",
            "hard_failures": [],
            "current": {
                "usage_events": [
                    {
                        "purpose": "review_conversation",
                        "input_tokens": 100,
                        "cached_input_tokens": 10,
                        "cache_write_tokens": 0,
                        "output_tokens": 20,
                        "latency_ms": 1000,
                        "estimated_cost_usd": 0.01,
                    }
                ]
            },
            "planning": {
                "score": {"pass": False, "move_pass": True, "question_ok": False},
                "usage_events": [
                    {
                        "purpose": "review_planning",
                        "input_tokens": 50,
                        "cached_input_tokens": 0,
                        "cache_write_tokens": 0,
                        "output_tokens": 10,
                        "latency_ms": 500,
                        "estimated_cost_usd": 0.002,
                    }
                ],
            },
        }
    ])

    summary = report["summary"]
    assert summary["planning_pass_rate"] == 0.0
    assert summary["planning_move_pass_rate"] == 1.0
    assert summary["realized_question_valid_rate"] == 0.0
    assert summary["usage_by_purpose"]["review_conversation"]["input_tokens"] == 100
    assert summary["usage_by_purpose"]["review_planning"]["output_tokens"] == 10
    assert summary["estimated_cost_usd"] == 0.012


def test_blind_human_acceptance_can_pass_only_with_complete_42_case_two_rater_set(tmp_path):
    import json
    from scripts.score_analytical_blind_review import score_packets

    key = []
    packet = []
    for index in range(1, 43):
        review_id = f"R{index:03d}"
        key.append({
            "review_id": review_id,
            "case_id": f"c{index}",
            "current_source": "live_current_engine",
            "A": "current",
            "B": "shadow",
        })
        packet.append({
            "review_id": review_id,
            "preference": "B",
            "hard_failures": {"A": [], "B": []},
            "dimension_scores": {
                "A": {"overall_next_move": 1},
                "B": {"overall_next_move": 2},
            },
        })

    key_path = tmp_path / "key.json"
    first = tmp_path / "rater1.json"
    second = tmp_path / "rater2.json"
    key_path.write_text(json.dumps(key))
    first.write_text(json.dumps(packet))
    second.write_text(json.dumps(packet))

    result = score_packets([first, second], key_path)
    assert result["ratings"] == 84
    assert result["distinct_cases"] == 42
    assert result["minimum_ratings_observed_per_case"] == 2
    assert result["preferences"]["shadow_rate"] == 1.0
    assert result["hard_failure_counts"]["shadow"] == 0
    assert result["acceptance"]["pass"] is True
