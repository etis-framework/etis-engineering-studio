from apps.api.app.services.review_planning import (
    CandidateMoveType,
    CandidateNextMove,
    ObjectiveConclusion,
    ObjectiveOutcome,
    ReasoningValidationMode,
    ReviewMode,
    ReviewObjectiveKind,
    ReviewPlanningMode,
    SelectionReasonCode,
    SubjectType,
    build_review_objective,
    canonical_review_mode,
    initialize_review_control,
    review_control_modes,
)


def challenge(**overrides):
    data = {
        "id": "finding-17",
        "phase_id": "A3",
        "lens": "chief_architect",
        "title": "Architecture claim under review",
        "prompt": "Test whether the current architecture claim is defensible.",
        "noticed": "The architecture document states a boundary that is not yet supported.",
        "evidence_refs": ["PATH:docs/architecture/system.md", "PATH:docs/architecture/system.md"],
        "finding": {
            "id": "finding-17",
            "title": "Unsupported architecture boundary",
            "statement": "The documented boundary is not supported by implementation evidence.",
        },
    }
    data.update(overrides)
    return data


def test_review_mode_compatibility_keeps_unknown_and_guided_modes_as_board_review():
    assert canonical_review_mode(None) is ReviewMode.BOARD_REVIEW
    assert canonical_review_mode("guided_review") is ReviewMode.BOARD_REVIEW
    assert canonical_review_mode("board_review") is ReviewMode.BOARD_REVIEW
    assert canonical_review_mode("focused_review") is ReviewMode.FOCUSED_REVIEW
    assert canonical_review_mode("finding_review") is ReviewMode.FINDING_REVIEW


def test_board_objective_is_bound_to_existing_challenge_without_score():
    objective = build_review_objective(
        raw_mode="guided_review",
        phase_id="A3",
        challenge=challenge(finding=None),
        objective_id="objective-board",
    )

    payload = objective.to_dict()
    assert objective.objective_kind is ReviewObjectiveKind.BOARD_POSITION
    assert objective.review_mode is ReviewMode.BOARD_REVIEW
    assert objective.subject.subject_type is SubjectType.CHALLENGE
    assert objective.subject.source_id == "finding-17"
    assert objective.evidence_refs == ("PATH:docs/architecture/system.md",)
    assert ObjectiveOutcome.CURRENT_POSITION_CLEAR in objective.required_outcomes
    assert ObjectiveOutcome.UNCERTAINTY_CLEAR in objective.optional_outcomes
    assert ObjectiveConclusion.UNRESOLVED_WITH_REASON in objective.permitted_conclusions
    assert objective.allows_unresolved is True
    assert "score" not in payload
    assert payload["objective_id"] == "objective-board"
    assert payload["review_mode"] == "board_review"


def test_focused_objective_preserves_exact_student_focus_and_does_not_require_position():
    focus = "I want to understand whether our service boundary matches the code."
    objective = build_review_objective(
        raw_mode="focused_review",
        phase_id="A3",
        challenge=challenge(id="focused-review", finding=None),
        focus=focus,
        objective_id="objective-focus",
    )

    assert objective.objective_kind is ReviewObjectiveKind.FOCUSED_ASSESSMENT
    assert objective.subject.subject_type is SubjectType.FOCUS
    assert objective.subject.statement == focus
    assert ObjectiveOutcome.FOCUS_UNDERSTOOD in objective.required_outcomes
    assert ObjectiveOutcome.CURRENT_POSITION_CLEAR not in objective.required_outcomes
    assert ObjectiveConclusion.EVIDENCE_BOUNDED_ASSESSMENT in objective.permitted_conclusions
    assert objective.derivation_codes == ("FOCUSED_REVIEW_STUDENT_CONCERN",)


def test_focused_objective_missing_focus_falls_back_without_inventing_student_concern():
    objective = build_review_objective(
        raw_mode="focused_review",
        phase_id="A3",
        challenge=challenge(id="focused-review", finding=None),
        focus="   ",
        objective_id="objective-focus-fallback",
    )

    assert objective.subject.subject_type is SubjectType.CHALLENGE
    assert objective.subject.statement == challenge()["noticed"]
    assert objective.derivation_codes == ("FOCUS_MISSING_FALLBACK_CHALLENGE",)


def test_finding_objective_can_challenge_reviewer_and_preserves_related_findings():
    objective = build_review_objective(
        raw_mode="finding_review",
        phase_id="A3",
        challenge=challenge(),
        related_finding_ids=["finding-17", "finding-18", "finding-18", "finding-19"],
        entry_intent="challenge",
        objective_id="objective-finding",
    )

    assert objective.objective_kind is ReviewObjectiveKind.FINDING_ANALYSIS
    assert objective.subject.subject_type is SubjectType.FINDING
    assert objective.subject.source_id == "finding-17"
    assert objective.subject.related_finding_ids == ("finding-18", "finding-19")
    assert ObjectiveOutcome.FINDING_EVIDENCE_TESTED in objective.required_outcomes
    assert ObjectiveConclusion.FINDING_CREDIBLY_CHALLENGED in objective.permitted_conclusions
    assert ObjectiveConclusion.CORRECTION_RECOMMENDED in objective.permitted_conclusions
    assert "FINDING_ENTRY_INTENT_CHALLENGE" in objective.derivation_codes


def test_finding_objective_with_no_valid_selected_finding_marks_legacy_fallback():
    objective = build_review_objective(
        raw_mode="finding_review",
        phase_id="A3",
        challenge=challenge(),
        related_finding_ids=[],
        entry_intent="review",
        objective_id="objective-finding-fallback",
    )

    assert objective.objective_kind is ReviewObjectiveKind.FINDING_ANALYSIS
    assert objective.subject.subject_type is SubjectType.CHALLENGE
    assert objective.required_outcomes == ()
    assert objective.derivation_codes[0] == "FINDING_SELECTION_MISSING_FALLBACK_CHALLENGE"


def test_review_control_serializes_objective_and_locks_explicit_modes():
    objective = build_review_objective(
        raw_mode="guided_review",
        phase_id="A3",
        challenge=challenge(finding=None),
        objective_id="objective-control",
    )
    control = initialize_review_control(
        objective,
        reasoning_mode=ReasoningValidationMode.LEGACY,
        planning_mode=ReviewPlanningMode.LEGACY,
    )

    assert control["schema_version"] == 1
    assert control["reasoning_mode"] == "legacy"
    assert control["planning_mode"] == "legacy"
    assert control["objective"]["objective_id"] == "objective-control"


def test_session_without_review_control_is_legacy_by_definition():
    assert review_control_modes({"reasoning_state": {"decision_explicit": True}}) == (
        ReasoningValidationMode.LEGACY,
        ReviewPlanningMode.LEGACY,
    )


def test_candidate_contract_contains_move_not_student_facing_question_text():
    candidate = CandidateNextMove(
        candidate_id="candidate-1",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
        reason_codes=(SelectionReasonCode.ADVANCES_OBJECTIVE,),
    )

    payload = candidate.to_dict()
    assert payload["move_type"] == "TEST_EVIDENCE_BOUNDARY"
    assert payload["target_outcome"] == "EVIDENCE_BOUNDARY_CLEAR"
    assert "question" not in payload
    assert "reply" not in payload


def test_pr1_configuration_defaults_to_legacy_modes():
    from apps.api.app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.etis_reasoning_validation_mode == "legacy"
    assert settings.etis_review_planning_mode == "legacy"


def test_pr2_configuration_allows_shadow_reasoning_mode():
    from apps.api.app.config import Settings

    settings = Settings(_env_file=None, etis_reasoning_validation_mode="shadow")
    assert settings.etis_reasoning_validation_mode == "shadow"


def test_pr2_configuration_fails_closed_for_validated_reasoning_mode():
    import pytest

    from apps.api.app.config import Settings

    with pytest.raises(ValueError, match="ETIS_REASONING_VALIDATION_MODE"):
        Settings(_env_file=None, etis_reasoning_validation_mode="validated")


def test_pr3_configuration_allows_shadow_planning_only_with_shadow_reasoning():
    import pytest

    from apps.api.app.config import Settings

    settings = Settings(
        _env_file=None,
        etis_reasoning_validation_mode="shadow",
        etis_review_planning_mode="shadow",
    )
    assert settings.etis_review_planning_mode == "shadow"

    with pytest.raises(ValueError, match="requires ETIS_REASONING_VALIDATION_MODE=shadow"):
        Settings(_env_file=None, etis_review_planning_mode="shadow")


def test_pr3_configuration_fails_closed_for_selected_planning_mode():
    import pytest

    from apps.api.app.config import Settings

    with pytest.raises(ValueError, match="ETIS_REVIEW_PLANNING_MODE"):
        Settings(
            _env_file=None,
            etis_reasoning_validation_mode="shadow",
            etis_review_planning_mode="selected",
        )
