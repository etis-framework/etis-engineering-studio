from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from apps.api.app.services.challenge_engine import Challenge, blank_reasoning, default_memory
from apps.api.app.services.reasoning_validation import (
    ReasoningDimension,
    ReasoningStatus,
    ValidationDecision,
    blank_reasoning_shadow,
)
from apps.api.app.services.review_planning import (
    CandidateMoveType,
    CandidateNextMove,
    PlanningContext,
    PlanningNeed,
    ReasoningValidationMode,
    ReviewPlanningMode,
    build_review_objective,
    canonical_review_mode,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "evals" / "analytical_engine_cases.json"


def load_cases(path: Path | str = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError("analytical eval corpus must be a JSON array")
    return [dict(row) for row in rows]


def filter_cases(
    rows: Sequence[Mapping[str, Any]],
    *,
    phase: str | None = None,
    case_ids: Iterable[str] | None = None,
    tags: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    ids = {str(value) for value in (case_ids or ()) if str(value)}
    wanted_tags = {str(value) for value in (tags or ()) if str(value)}
    selected: list[dict[str, Any]] = []
    for row in rows:
        if phase and str(row.get("phase_id")) != phase:
            continue
        if ids and str(row.get("id")) not in ids:
            continue
        row_tags = {str(value) for value in (row.get("tags") or ())}
        if wanted_tags and not wanted_tags.intersection(row_tags):
            continue
        selected.append(dict(row))
    return selected


def build_objective(case: Mapping[str, Any]):
    return build_review_objective(
        raw_mode=str(case.get("review_mode") or "board_review"),
        phase_id=str(case.get("phase_id") or "A1"),
        challenge=dict(case.get("challenge") or {}),
        focus=str(case.get("focus") or ""),
        related_finding_ids=tuple(case.get("related_finding_ids") or ()),
        entry_intent=str((case.get("student") or {}).get("intent") or "review"),
        objective_id=f"eval-{case.get('id')}",
    )




def build_legacy_challenge(case: Mapping[str, Any]) -> Challenge:
    raw = dict(case.get("challenge") or {})
    legacy = dict(case.get("legacy_engine") or {})
    noticed = str(raw.get("noticed") or (case.get("scenario") or {}).get("statement") or "")
    title = str(raw.get("title") or (case.get("scenario") or {}).get("title") or "Analytical review")
    return Challenge(
        id=str(raw.get("id") or f"eval-{case.get('id')}"),
        phase_id=str(case.get("phase_id") or "A1"),
        lens=str(legacy.get("reviewer_lens") or "chief_architect"),
        title=title,
        prompt=f"{title}. {noticed}".strip(),
        why_now="Synthetic PR4 analytical evaluation case bounded to the supplied frozen evidence.",
        evidence_refs=[str(value) for value in (raw.get("evidence_refs") or ())],
        dimensions=[],
        expected_move="Develop the next defensible engineering move from the supplied evidence and student reasoning.",
        noticed=noticed,
        significance=str((case.get("scenario") or {}).get("statement") or noticed),
        decision_question=str(legacy.get("question") or ""),
        finding=(dict(raw.get("finding")) if isinstance(raw.get("finding"), Mapping) else None),
        strengths=[],
    )


def build_legacy_reasoning_state(case: Mapping[str, Any]) -> dict[str, bool]:
    state = blank_reasoning()
    for dimension, status in dict(case.get("validated_reasoning") or {}).items():
        if dimension in state:
            state[dimension] = str(status) == ReasoningStatus.VALIDATED.value
    return state


def build_legacy_conversation_memory(case: Mapping[str, Any]) -> dict[str, Any]:
    legacy = dict(case.get("legacy_engine") or {})
    memory = default_memory(str(legacy.get("reviewer_lens") or "chief_architect"))
    memory.update(
        {
            "review_mode": str(case.get("review_mode") or "board_review"),
            "review_focus": str(case.get("focus") or ""),
            "entry_intent": "review",
            "requested_finding_ids": [str(value) for value in (case.get("related_finding_ids") or ())],
            "source_view": "analytical_eval",
        }
    )
    return memory


def build_legacy_conversation_history(case: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    context = dict(case.get("context") or {})
    questions = [str(value) for value in (context.get("recent_questions") or ()) if str(value)]
    student_turns = [str(value) for value in (context.get("recent_student_turns") or ()) if str(value)]
    history: list[dict[str, str]] = []
    for index in range(max(len(questions), len(student_turns))):
        if index < len(questions):
            history.append({"actor": "reviewer", "lens": str((case.get("legacy_engine") or {}).get("reviewer_lens") or "chief_architect"), "content": questions[index]})
        if index < len(student_turns):
            history.append({"actor": "student", "lens": "", "content": student_turns[index]})
    return tuple(history[-20:])

def build_shadow_reasoning(case: Mapping[str, Any]) -> dict[str, Any]:
    shadow = blank_reasoning_shadow()
    supplied = dict(case.get("validated_reasoning") or {})
    for dimension in ReasoningDimension:
        status = str(supplied.get(dimension.value) or ReasoningStatus.UNESTABLISHED.value)
        if status not in {item.value for item in ReasoningStatus}:
            raise ValueError(f"invalid reasoning status {status!r} for {dimension.value}")
        shadow["dimensions"][dimension.value]["status"] = status
    return shadow


def build_planning_context(
    case: Mapping[str, Any],
    current_engine: Mapping[str, Any] | None = None,
) -> PlanningContext:
    objective = build_objective(case)
    student = dict(case.get("student") or {})
    context = dict(case.get("context") or {})
    evidence_package = dict(case.get("evidence_package") or {})
    current = dict(current_engine or {})
    assistance_state = dict(context.get("assistance_state") or {})
    assistance_state.update(
        {
            "interpreted_intent": str(
                current.get("interpreted_intent")
                or assistance_state.get("interpreted_intent")
                or student.get("intent")
                or "other"
            ),
            "teaching_needed": bool(
                current.get("teach_back")
                or current.get("kind") == "teaching"
                or assistance_state.get("teaching_needed")
            ),
            "legacy_target": str(
                current.get("target_move")
                or assistance_state.get("legacy_target")
                or ""
            ),
        }
    )
    return PlanningContext(
        session_id=None,
        phase_id=str(case.get("phase_id") or "A1"),
        review_mode=canonical_review_mode(str(case.get("review_mode") or "board_review")),
        reasoning_mode=ReasoningValidationMode.SHADOW,
        planning_mode=ReviewPlanningMode.SHADOW,
        objective=objective,
        snapshot_id=1,
        commit_sha=f"eval-{case.get('id')}-sha",
        evidence_package=evidence_package,
        objective_evidence_refs=tuple(objective.evidence_refs),
        current_challenge=dict(case.get("challenge") or {}),
        current_findings=tuple(dict(item) for item in (context.get("current_findings") or ())),
        finding_states=tuple(dict(item) for item in (context.get("finding_states") or ())),
        focus=str(case.get("focus") or ""),
        legacy_reasoning_state={},
        validated_reasoning_state=build_shadow_reasoning(case),
        reasoning_authority="shadow_validated",
        recent_questions=tuple(context.get("recent_questions") or ()),
        recent_student_turns=tuple(context.get("recent_student_turns") or ()),
        latest_student_turn=str(student.get("turn") or ""),
        latest_student_evidence_refs=tuple(student.get("evidence_refs") or ()),
        conversation_memory={},
        reviewer_corrections=tuple(dict(item) for item in (context.get("reviewer_corrections") or ())),
        evidence_disputes=tuple(dict(item) for item in (context.get("evidence_disputes") or ())),
        explicit_uncertainty=tuple(context.get("explicit_uncertainty") or ()),
        current_position=str(student.get("decision") or ""),
        committed_position=None,
        coaching_level=1,
        assistance_state=assistance_state,
        active_reviewer_lens=str(
            current.get("reviewer_lens")
            or (case.get("legacy_engine") or {}).get("reviewer_lens")
            or "chief_architect"
        ),
    )


def oracle_candidates(case: Mapping[str, Any]) -> tuple[CandidateNextMove, ...]:
    result: list[CandidateNextMove] = []
    for raw in case.get("oracle_candidates") or ():
        result.append(
            CandidateNextMove(
                candidate_id=str(raw["candidate_id"]),
                move_type=CandidateMoveType(str(raw["move_type"])),
                target_outcome=_objective_outcome(str(raw["target_outcome"])),
                evidence_refs=tuple(raw.get("evidence_refs") or ()),
                preferred_reviewer_lens=(str(raw.get("preferred_reviewer_lens") or "") or None),
                teaching_required=bool(raw.get("teaching_required", False)),
            )
        )
    return tuple(result)


def reasoning_probe(case: Mapping[str, Any]) -> tuple[dict[str, bool], dict[str, set[str]]]:
    raw = dict(case.get("reasoning_probe") or {})
    updates = {str(key): bool(value) for key, value in dict(raw.get("proposal_updates") or {}).items()}
    acceptable = {
        str(dimension): {str(value) for value in values}
        for dimension, values in dict(raw.get("acceptable_decisions") or {}).items()
    }
    return updates, acceptable


def score_reasoning_signal(case: Mapping[str, Any], signal: Mapping[str, Any]) -> dict[str, Any]:
    _, expected = reasoning_probe(case)
    observed = {
        str(item.get("dimension")): str(item.get("decision"))
        for item in (signal.get("evaluations") or ())
        if isinstance(item, Mapping)
    }
    details = []
    passed = True
    for dimension, acceptable in expected.items():
        got = observed.get(dimension)
        ok = got in acceptable
        details.append({
            "dimension": dimension,
            "observed": got,
            "acceptable": sorted(acceptable),
            "pass": ok,
        })
        passed = passed and ok
    return {"pass": passed, "details": details}


def score_planning_signal(case: Mapping[str, Any], signal: Mapping[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expectations") or {})
    shadow = dict(signal.get("shadow_planner") or {})
    primary_need = str(shadow.get("primary_need") or signal.get("primary_need") or "")
    move = str(shadow.get("selected_move_type") or "")
    target = str(shadow.get("target_outcome") or "")
    question = str(shadow.get("proposed_question") or "")
    acceptable_moves = {str(value) for value in (expected.get("acceptable_moves") or ())}
    acceptable_targets = {str(value) for value in (expected.get("acceptable_target_outcomes") or ())}
    forbidden_moves = {str(value) for value in (expected.get("forbidden_moves") or ())}
    acceptable_paths = _planning_paths(expected.get("acceptable_planning_paths") or ())
    preferred_paths = _planning_paths(expected.get("preferred_planning_paths") or ())
    observed_path = (primary_need, move, target)
    path_contract_active = bool(acceptable_paths)
    path_ok = observed_path in acceptable_paths if path_contract_active else None
    preferred_path_match = observed_path in preferred_paths if preferred_paths else False
    status_ok = str(signal.get("status") or "") == "completed"
    target_ok = target in acceptable_targets
    explicit_move_match = move in acceptable_moves
    preferred_move_match = move in {
        str(value) for value in (expected.get("preferred_moves") or ())
    }
    # Backward compatibility: cases without explicit planning paths preserve the
    # PR4A/PR4F selector-valid-target scoring contract. Migrated PR4H cases use
    # the complete Need -> Move -> Target tuple as the semantic acceptance unit.
    semantic_ok = bool(path_ok) if path_contract_active else target_ok
    move_ok = bool(move) and move not in forbidden_moves and semantic_ok
    question_ok = bool(question.strip()) and question.count("?") == 1
    path_pass = (status_ok and move_ok) if path_contract_active else None
    legacy_target_move_pass = status_ok and bool(move) and move not in forbidden_moves and target_ok
    move_pass = bool(path_pass) if path_contract_active else legacy_target_move_pass
    return {
        "pass": move_pass and question_ok,
        "move_pass": move_pass,
        "path_pass": path_pass,
        "legacy_target_move_pass": legacy_target_move_pass,
        "status_ok": status_ok,
        "move_ok": move_ok,
        "target_ok": target_ok,
        "path_contract_active": path_contract_active,
        "path_ok": path_ok,
        "preferred_path_match": preferred_path_match,
        "explicit_move_match": explicit_move_match,
        "preferred_move_match": preferred_move_match,
        "question_ok": question_ok,
        "observed_primary_need": primary_need,
        "observed_move": move,
        "observed_target": target,
        "observed_path": list(observed_path),
        "acceptable_paths": [list(value) for value in sorted(acceptable_paths)],
        "preferred_paths": [list(value) for value in sorted(preferred_paths)],
        "acceptable_moves": sorted(acceptable_moves),
        "acceptable_targets": sorted(acceptable_targets),
        "forbidden_moves": sorted(forbidden_moves),
        "question": question,
    }


def _planning_paths(values: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    return {
        (
            str(value.get("primary_need") or ""),
            str(value.get("move_type") or ""),
            str(value.get("target_outcome") or ""),
        )
        for value in values
        if isinstance(value, Mapping)
    }


def validate_enum_contract(case: Mapping[str, Any]) -> None:
    from apps.api.app.services.review_planning import ObjectiveOutcome

    canonical_review_mode(str(case.get("review_mode") or ""))
    expectations = dict(case.get("expectations") or {})
    for value in expectations.get("acceptable_moves") or ():
        CandidateMoveType(str(value))
    for value in expectations.get("forbidden_moves") or ():
        CandidateMoveType(str(value))
    for value in expectations.get("acceptable_target_outcomes") or ():
        ObjectiveOutcome(str(value))
    acceptable_paths = _validate_planning_paths(
        expectations.get("acceptable_planning_paths") or (),
        field="acceptable_planning_paths",
    )
    preferred_paths = _validate_planning_paths(
        expectations.get("preferred_planning_paths") or (),
        field="preferred_planning_paths",
    )
    if preferred_paths and not preferred_paths.issubset(acceptable_paths):
        raise ValueError("preferred_planning_paths must be a subset of acceptable_planning_paths")
    updates, acceptable = reasoning_probe(case)
    valid_dimensions = {item.value for item in ReasoningDimension}
    valid_decisions = {item.value for item in ValidationDecision}
    if not set(updates).issubset(valid_dimensions):
        raise ValueError(f"unknown reasoning dimension(s): {sorted(set(updates)-valid_dimensions)}")
    for dimension, values in acceptable.items():
        if dimension not in updates:
            raise ValueError(f"reasoning expectation {dimension} has no proposal")
        if not values or not values.issubset(valid_decisions):
            raise ValueError(f"invalid acceptable decisions for {dimension}: {sorted(values)}")


def _validate_planning_paths(
    values: Iterable[Mapping[str, Any]],
    *,
    field: str,
) -> set[tuple[str, str, str]]:
    from apps.api.app.services.review_planning import ObjectiveOutcome

    result: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        required = {"primary_need", "move_type", "target_outcome"}
        missing = required - set(raw)
        if missing:
            raise ValueError(f"{field}[{index}] missing fields: {sorted(missing)}")
        need = PlanningNeed(str(raw["primary_need"])).value
        move = CandidateMoveType(str(raw["move_type"])).value
        target = ObjectiveOutcome(str(raw["target_outcome"])).value
        result.add((need, move, target))
    return result


def _objective_outcome(value: str):
    from apps.api.app.services.review_planning import ObjectiveOutcome
    return ObjectiveOutcome(value)
