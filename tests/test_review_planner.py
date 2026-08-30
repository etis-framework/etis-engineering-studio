from dataclasses import replace

from apps.api.app.services.reasoning_validation import blank_reasoning_shadow
from apps.api.app.services.next_question_selector import NextQuestionSelector
from apps.api.app.services.review_planner import ReviewPlanner, blank_planning_shadow
from apps.api.app.services.review_planning import (
    CandidateMoveType,
    CandidateNextMove,
    CandidateRejectionCode,
    ObjectiveOutcome,
    PlanningContext,
    PlanningNeed,
    ReasoningValidationMode,
    ReviewPlanningMode,
    SelectionReasonCode,
    build_review_objective,
)


def challenge():
    return {
        "id": "finding-17",
        "phase_id": "A3",
        "lens": "chief_architect",
        "title": "Architecture claim under review",
        "prompt": "Test whether the current architecture claim is supportable.",
        "noticed": "The architecture claim needs evidence.",
        "evidence_refs": ["PATH:docs/architecture/system.md"],
        "finding": {
            "id": "finding-17",
            "title": "Architecture claim under review",
            "statement": "The architecture claim may not be supported.",
            "evidence_refs": ["PATH:docs/architecture/system.md"],
        },
    }


def planning_context(*, intent="reasoning", recent_questions=(), shadow=None, explicit_uncertainty=()):
    objective = build_review_objective(
        raw_mode="board_review",
        phase_id="A3",
        challenge=challenge(),
        objective_id="objective-1",
    )
    return PlanningContext(
        session_id=7,
        phase_id="A3",
        review_mode=objective.review_mode,
        reasoning_mode=ReasoningValidationMode.SHADOW,
        planning_mode=ReviewPlanningMode.SHADOW,
        objective=objective,
        snapshot_id=11,
        commit_sha="abc123",
        evidence_package={
            "phase_id": "A3",
            "commit_sha": "abc123",
            "challenge": {"finding": challenge()["finding"]},
            "relevant_items": [
                {
                    "ref": "EV-A3-ARCH",
                    "title": "docs/architecture/system.md",
                    "status": "present",
                }
            ],
            "relevant_artifacts": [
                {
                    "path": "docs/architecture/system.md",
                    "summary": "Architecture boundaries and responsibilities.",
                }
            ],
        },
        objective_evidence_refs=objective.evidence_refs,
        current_challenge=challenge(),
        current_findings=(challenge()["finding"],),
        validated_reasoning_state=shadow or blank_reasoning_shadow(),
        reasoning_authority="shadow_validated_context_legacy_student_authority",
        recent_questions=tuple(recent_questions),
        recent_student_turns=("We chose this boundary because it limits coupling.",),
        latest_student_turn="The repository shows the component boundary, but not its failure behavior.",
        latest_student_evidence_refs=("PATH:docs/architecture/system.md",),
        explicit_uncertainty=tuple(explicit_uncertainty),
        assistance_state={"interpreted_intent": intent, "teaching_needed": intent == "stuck"},
        active_reviewer_lens="chief_architect",
    )


class FakePlannerAI:
    def __init__(
        self,
        *,
        plan_payload=None,
        realization_payload=None,
        realization_payloads=None,
        plan_error=None,
        realization_error=None,
    ):
        self.plan_payload = plan_payload or {
            "primary_need": "EVIDENCE_DEFICIT",
            "candidates": [
                {
                    "candidate_id": "evidence",
                    "move_type": "TEST_EVIDENCE_BOUNDARY",
                    "target_outcome": "EVIDENCE_BOUNDARY_CLEAR",
                    "evidence_refs": ["PATH:docs/architecture/system.md"],
                    "preferred_reviewer_lens": "evidence_auditor",
                    "teaching_required": False,
                    "reason_codes": ["EVIDENCE_GROUNDED"],
                },
                {
                    "candidate_id": "consequence",
                    "move_type": "CLARIFY_CONSEQUENCE",
                    "target_outcome": "ENGINEERING_CONSEQUENCE_CLEAR",
                    "evidence_refs": [],
                    "preferred_reviewer_lens": "chief_architect",
                    "teaching_required": False,
                    "reason_codes": ["HIGH_ENGINEERING_CONSEQUENCE"],
                },
            ],
            "_usage": {"purpose": "review_planning_shadow", "estimated_cost_usd": 0.001},
        }
        self.realization_payload = realization_payload or {
            "lead_in": "Your boundary claim is specific enough to test against the frozen evidence.",
            "question": "What does the frozen architecture evidence establish, and what does it still leave unsupported?",
            "_usage": {"purpose": "review_move_realization_shadow", "estimated_cost_usd": 0.001},
        }
        self.realization_payloads = list(realization_payloads or ())
        self.plan_error = plan_error
        self.realization_error = realization_error
        self.plan_calls = 0
        self.realization_calls = 0
        self.last_plan_system = ""
        self.last_plan_user = ""
        self.last_realizer_system = ""
        self.last_realizer_user = ""

    def available(self):
        return True

    def plan_review_turn(self, system_prompt, user_prompt):
        self.plan_calls += 1
        self.last_plan_system = system_prompt
        self.last_plan_user = user_prompt
        if self.plan_error:
            raise self.plan_error
        return self.plan_payload

    def realize_review_move(self, system_prompt, user_prompt):
        self.realization_calls += 1
        self.last_realizer_system = system_prompt
        self.last_realizer_user = user_prompt
        if self.realization_error:
            raise self.realization_error
        if self.realization_payloads:
            index = min(self.realization_calls - 1, len(self.realization_payloads) - 1)
            return self.realization_payloads[index]
        return self.realization_payload


def test_shadow_planner_selects_move_before_separate_realizer_phrases_question():
    ai = FakePlannerAI()
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=blank_planning_shadow(),
        current_engine={
            "target_move": "consequence_visible",
            "reviewer_lens": "chief_architect",
            "question": "What engineering consequence follows from that choice?",
        },
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert ai.plan_calls == 1
    assert ai.realization_calls == 1
    assert outcome.signal["status"] == "completed"
    assert outcome.signal["shadow_planner"]["selected_candidate_id"] == "evidence"
    assert outcome.signal["shadow_planner"]["selected_move_type"] == "TEST_EVIDENCE_BOUNDARY"
    assert outcome.signal["shadow_planner"]["target_outcome"] == "EVIDENCE_BOUNDARY_CLEAR"
    assert outcome.signal["shadow_planner"]["proposed_question"].startswith("What does the frozen")
    assert outcome.signal["comparison"]["same_target_as_legacy"] is False
    assert outcome.shadow_state["comparison"]["completed_plans"] == 1
    assert [event["purpose"] for event in outcome.usage_events] == [
        "review_planning_shadow",
        "review_move_realization_shadow",
    ]


def test_neither_shadow_model_call_receives_current_engine_reply():
    ai = FakePlannerAI()
    ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={
            "target_move": "consequence_visible",
            "reviewer_lens": "chief_architect",
            "question": "LEGACY SECRET QUESTION?",
        },
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert "LEGACY SECRET QUESTION" not in ai.last_plan_user
    assert "LEGACY SECRET QUESTION" not in ai.last_realizer_user
    assert "Do NOT draft the student-facing question" in ai.last_plan_system
    assert "LOCKED exactly one engineering move" in ai.last_realizer_system


def test_realizer_receives_only_selected_move_not_unselected_candidate_agenda():
    ai = FakePlannerAI()
    ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )
    assert '"candidate_id":"evidence"' in ai.last_realizer_user
    assert '"candidate_id":"consequence"' not in ai.last_realizer_user


def test_selector_rejects_invented_evidence_reference():
    selector = NextQuestionSelector()
    context = planning_context()
    bad = CandidateNextMove(
        candidate_id="bad",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:invented.md",),
    )
    good = CandidateNextMove(
        candidate_id="good",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )

    selected, _ = selector.select(context=context, candidates=(bad, good))

    assert selected.selected_candidate_id == "good"
    rejected = {item.candidate_id: item for item in selected.rejected_candidates}
    assert CandidateRejectionCode.NO_FROZEN_EVIDENCE_BASIS in rejected["bad"].rejection_codes


def test_selector_rejects_move_that_only_reasks_an_already_validated_outcome():
    shadow = blank_reasoning_shadow()
    shadow["dimensions"]["consequence_visible"]["status"] = "validated"
    selector = NextQuestionSelector()
    context = planning_context(shadow=shadow)
    evidence = CandidateNextMove(
        candidate_id="evidence",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
    )
    consequence = CandidateNextMove(
        candidate_id="consequence",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )

    selected, _ = selector.select(context=context, candidates=(evidence, consequence))

    assert selected.selected_candidate_id == "evidence"
    rejected = {item.candidate_id: item for item in selected.rejected_candidates}
    assert CandidateRejectionCode.ALREADY_ESTABLISHED in rejected["consequence"].rejection_codes


def test_selector_requires_teaching_move_when_student_is_stuck():
    selector = NextQuestionSelector()
    context = planning_context(intent="stuck")
    normal = CandidateNextMove(
        candidate_id="normal",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
    )
    teach = CandidateNextMove(
        candidate_id="teach",
        move_type=CandidateMoveType.TEACH_CONCEPT,
        target_outcome=ObjectiveOutcome.CURRENT_POSITION_CLEAR,
        teaching_required=True,
    )

    selected, _ = selector.select(context=context, candidates=(normal, teach))

    assert selected.selected_candidate_id == "teach"
    assert SelectionReasonCode.MATCHES_ASSISTANCE_LEVEL in selected.reason_codes
    rejected = {item.candidate_id: item for item in selected.rejected_candidates}
    assert CandidateRejectionCode.TEACHING_REQUIRED_FIRST in rejected["normal"].rejection_codes


def test_selector_prioritizes_student_challenge_before_returning_to_agenda():
    selector = NextQuestionSelector()
    context = planning_context(intent="evidence_dispute")
    normal = CandidateNextMove(
        candidate_id="normal",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )
    challenge_move = CandidateNextMove(
        candidate_id="challenge",
        move_type=CandidateMoveType.ADDRESS_STUDENT_CHALLENGE,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
    )

    selected, _ = selector.select(context=context, candidates=(normal, challenge_move))

    assert selected.selected_candidate_id == "challenge"
    assert SelectionReasonCode.ADDRESSES_STUDENT_CHALLENGE in selected.reason_codes


def test_selector_prefers_evidence_test_over_generic_consequence_when_both_are_unresolved():
    selector = NextQuestionSelector()
    context = planning_context()
    evidence = CandidateNextMove(
        candidate_id="evidence",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
    )
    consequence = CandidateNextMove(
        candidate_id="consequence",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )

    selected, _ = selector.select(context=context, candidates=(consequence, evidence))

    assert selected.selected_candidate_id == "evidence"


def test_selector_prioritizes_explicit_uncertainty_over_generic_consequence():
    selector = NextQuestionSelector()
    context = planning_context(explicit_uncertainty=("External behavior is not yet known.",))
    uncertainty = CandidateNextMove(
        candidate_id="uncertainty",
        move_type=CandidateMoveType.SURFACE_UNCERTAINTY,
        target_outcome=ObjectiveOutcome.UNCERTAINTY_CLEAR,
    )
    consequence = CandidateNextMove(
        candidate_id="consequence",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )

    selected, _ = selector.select(context=context, candidates=(consequence, uncertainty))

    assert selected.selected_candidate_id == "uncertainty"
    assert SelectionReasonCode.PRESERVES_VALID_UNCERTAINTY in selected.reason_codes


def test_selector_respects_planner_teaching_signal_even_when_upstream_intent_is_reasoning():
    selector = NextQuestionSelector()
    context = planning_context(intent="reasoning")
    teach = CandidateNextMove(
        candidate_id="teach",
        move_type=CandidateMoveType.TEACH_CONCEPT,
        target_outcome=ObjectiveOutcome.CURRENT_POSITION_CLEAR,
        teaching_required=True,
    )
    consequence = CandidateNextMove(
        candidate_id="consequence",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )

    selected, _ = selector.select(context=context, candidates=(consequence, teach))

    assert selected.selected_candidate_id == "teach"
    assert SelectionReasonCode.MATCHES_ASSISTANCE_LEVEL in selected.reason_codes


def test_selector_allows_evidence_testing_to_deepen_validated_reasoning_without_reasking_it():
    selector = NextQuestionSelector()
    shadow = blank_reasoning_shadow()
    shadow["dimensions"]["evidence_boundary_visible"]["status"] = "validated"
    context = planning_context(shadow=shadow)
    evidence = CandidateNextMove(
        candidate_id="evidence",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
    )

    selected, rejected = selector.select(context=context, candidates=(evidence,))

    assert selected is not None
    assert selected.selected_candidate_id == "evidence"
    assert not rejected


def test_planner_adds_bounded_teaching_fallback_when_required_and_model_omits_one():
    ai = FakePlannerAI(
        plan_payload={
            "candidates": [
                {
                    "candidate_id": "ordinary",
                    "move_type": "CLARIFY_CONSEQUENCE",
                    "target_outcome": "ENGINEERING_CONSEQUENCE_CLEAR",
                    "evidence_refs": [],
                    "preferred_reviewer_lens": "chief_architect",
                    "teaching_required": False,
                    "reason_codes": [],
                }
            ],
            "_usage": {"purpose": "review_planning_shadow"},
        },
        realization_payload={
            "lead_in": "A boundary is only defensible if you can explain the reasoning behind it.",
            "question": "In your own words, what makes this boundary defensible?",
        },
    )
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(intent="stuck"),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "completed"
    shadow = outcome.signal["shadow_planner"]
    assert shadow["selected_candidate_id"] == "app-bounded-teaching-fallback"
    assert shadow["selected_move_type"] == "TEACH_CONCEPT"
    assert shadow["teaching_required"] is True


def test_planning_signal_records_candidate_moves_for_post_run_diagnosis():
    outcome = ReviewPlanner(ai=FakePlannerAI()).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    candidates = outcome.signal["shadow_planner"]["candidate_moves"]
    assert [item["candidate_id"] for item in candidates] == ["evidence", "consequence"]
    assert candidates[0]["move_type"] == "TEST_EVIDENCE_BOUNDARY"



def test_selector_uses_semantic_primary_need_before_objective_checklist_order():
    selector = NextQuestionSelector()
    context = planning_context()
    position = CandidateNextMove(
        candidate_id="position",
        move_type=CandidateMoveType.MAKE_POSITION_EXPLICIT,
        target_outcome=ObjectiveOutcome.CURRENT_POSITION_CLEAR,
    )
    evidence = CandidateNextMove(
        candidate_id="evidence",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
    )

    selected, _ = selector.select(
        context=context,
        candidates=(position, evidence),
        semantic_need=PlanningNeed.EVIDENCE_DEFICIT,
    )

    assert selected.selected_candidate_id == "evidence"
    assert selected.primary_need is PlanningNeed.EVIDENCE_DEFICIT
    assert SelectionReasonCode.MATCHES_PRIMARY_NEED in selected.reason_codes


def test_evidence_backed_student_challenge_is_application_required_before_downstream_change():
    selector = NextQuestionSelector()
    base = planning_context(intent="evidence_dispute")
    finding_objective = build_review_objective(
        raw_mode="finding_review",
        phase_id="A3",
        challenge=challenge(),
        related_finding_ids=("finding-17",),
        objective_id="finding-objective-1",
    )
    context = replace(
        base,
        review_mode=finding_objective.review_mode,
        objective=finding_objective,
        evidence_disputes=({"finding_id": "finding-17", "status": "present"},),
        finding_states=({"finding_id": "finding-17", "status": "evidence_disputed"},),
    )
    evidence_test = CandidateNextMove(
        candidate_id="evidence-test",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.FINDING_EVIDENCE_TESTED,
        evidence_refs=("PATH:docs/architecture/system.md",),
    )
    downstream = CandidateNextMove(
        candidate_id="downstream",
        move_type=CandidateMoveType.ESTABLISH_CHANGE_TRIGGER,
        target_outcome=ObjectiveOutcome.NEXT_ACTION_OR_UNCERTAINTY_CLEAR,
    )

    selected, rejected = selector.select(
        context=context,
        candidates=(downstream, evidence_test),
        semantic_need=PlanningNeed.ACTION_OR_CHANGE,
    )

    assert selected.selected_candidate_id == "evidence-test"
    assert selected.primary_need is PlanningNeed.STUDENT_CHALLENGE
    assert selected.primary_need_source.value == "application"
    rejected_by_id = {item.candidate_id: item for item in rejected}
    assert (
        CandidateRejectionCode.DOES_NOT_ADDRESS_REQUIRED_NEED
        in rejected_by_id["downstream"].rejection_codes
    )


def test_independent_judgment_need_beats_downstream_change_without_global_move_bonus():
    selector = NextQuestionSelector()
    context = planning_context()
    position = CandidateNextMove(
        candidate_id="position",
        move_type=CandidateMoveType.MAKE_POSITION_EXPLICIT,
        target_outcome=ObjectiveOutcome.CURRENT_POSITION_CLEAR,
    )
    change = CandidateNextMove(
        candidate_id="change",
        move_type=CandidateMoveType.ESTABLISH_CHANGE_TRIGGER,
        target_outcome=ObjectiveOutcome.CHANGE_OR_CLOSURE_CONDITION_CLEAR,
    )

    selected, _ = selector.select(
        context=context,
        candidates=(change, position),
        semantic_need=PlanningNeed.INDEPENDENT_JUDGMENT,
    )

    assert selected.selected_candidate_id == "position"
    assert selected.primary_need is PlanningNeed.INDEPENDENT_JUDGMENT


def test_non_teaching_move_cannot_gain_teaching_authority_from_boolean():
    selector = NextQuestionSelector()
    context = planning_context(intent="stuck")
    mislabeled = CandidateNextMove(
        candidate_id="mislabeled",
        move_type=CandidateMoveType.TEST_EVIDENCE_BOUNDARY,
        target_outcome=ObjectiveOutcome.EVIDENCE_BOUNDARY_CLEAR,
        evidence_refs=("PATH:docs/architecture/system.md",),
        teaching_required=True,
    )
    teach = CandidateNextMove(
        candidate_id="teach",
        move_type=CandidateMoveType.TEACH_CONCEPT,
        target_outcome=ObjectiveOutcome.CURRENT_POSITION_CLEAR,
        teaching_required=True,
    )

    selected, rejected = selector.select(context=context, candidates=(mislabeled, teach))

    assert selected.selected_candidate_id == "teach"
    rejected_by_id = {item.candidate_id: item for item in rejected}
    assert CandidateRejectionCode.TEACHING_REQUIRED_FIRST in rejected_by_id["mislabeled"].rejection_codes


def test_planner_adds_selectable_teaching_fallback_when_model_teaching_candidate_is_outside_objective():
    ai = FakePlannerAI(
        plan_payload={
            "primary_need": "TEACHING_OR_TEACHBACK",
            "candidates": [
                {
                    "candidate_id": "bad-teach",
                    "move_type": "TEACH_CONCEPT",
                    "target_outcome": "FOCUS_UNDERSTOOD",
                    "evidence_refs": [],
                    "preferred_reviewer_lens": "chief_architect",
                    "teaching_required": True,
                    "reason_codes": [],
                }
            ],
        },
        realization_payload={
            "lead_in": "A defensible position must be explainable in your own words.",
            "question": "What is your current position and why do you hold it?",
        },
    )

    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(intent="stuck"),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "completed"
    assert outcome.signal["shadow_planner"]["selected_candidate_id"] == "app-bounded-teaching-fallback"
    assert outcome.signal["shadow_planner"]["primary_need"] == "TEACHING_OR_TEACHBACK"


def test_planner_adds_uncertainty_continuity_fallback_instead_of_reasking_evidence_boundary():
    ai = FakePlannerAI(
        plan_payload={
            "primary_need": "EVIDENCE_DEFICIT",
            "candidates": [
                {
                    "candidate_id": "evidence",
                    "move_type": "TEST_EVIDENCE_BOUNDARY",
                    "target_outcome": "EVIDENCE_BOUNDARY_CLEAR",
                    "evidence_refs": ["PATH:docs/architecture/system.md"],
                    "preferred_reviewer_lens": "evidence_auditor",
                    "teaching_required": False,
                    "reason_codes": [],
                }
            ],
        },
        realization_payload={
            "lead_in": "",
            "question": "What evidence or decision would resolve the uncertainty you have identified?",
        },
    )

    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(explicit_uncertainty=("Failure behavior is not established.",)),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "completed"
    shadow = outcome.signal["shadow_planner"]
    assert shadow["primary_need"] == "UNCERTAINTY"
    assert shadow["primary_need_source"] == "application"
    assert shadow["selected_candidate_id"] == "app-bounded-uncertainty-fallback"
    assert shadow["selected_move_type"] == "SURFACE_UNCERTAINTY"


def test_realizer_repairs_invalid_wording_once_without_replanning_or_changing_move():
    ai = FakePlannerAI(
        realization_payloads=[
            {
                "lead_in": "",
                "question": "What A4 implementation artifact will prove this A3 architecture decision?",
                "_usage": {"purpose": "review_move_realization_shadow"},
            },
            {
                "lead_in": "",
                "question": "What current A3 evidence would make you revise this architecture position?",
                "_usage": {"purpose": "review_move_realization_shadow"},
            },
        ]
    )

    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "completed"
    assert ai.plan_calls == 1
    assert ai.realization_calls == 2
    shadow = outcome.signal["shadow_planner"]
    assert shadow["selected_candidate_id"] == "evidence"
    assert shadow["realization_repair"]["attempted"] is True
    assert shadow["realization_repair"]["succeeded"] is True
    assert shadow["realization_repair"]["initial_rejection_codes"] == ["FUTURE_PHASE_DEMAND"]
    assert outcome.shadow_state["comparison"]["realization_repair_attempts"] == 1
    assert outcome.shadow_state["comparison"]["realization_repair_successes"] == 1
    assert "previous wording was rejected" in ai.last_realizer_system


def test_planner_prompt_prioritizes_first_order_defects_over_checklist_coverage():
    ai = FakePlannerAI()
    ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert "already states a meaningful consequence" in ai.last_plan_system
    assert "first-order defects" in ai.last_plan_system
    assert "not a checklist order" in ai.last_plan_system
    assert "primary_need" in ai.last_plan_system
    assert "INDEPENDENT_JUDGMENT" in ai.last_plan_system


def test_realizer_rejects_future_phase_question_after_selection():
    ai = FakePlannerAI(
        realization_payload={
            "lead_in": "",
            "question": "What A4 implementation artifact will prove this A3 architecture decision?",
        }
    )
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert outcome.signal["failure_stage"] == "realizer_validation"
    assert "FUTURE_PHASE_DEMAND" in outcome.signal["realization_rejection_codes"]
    assert outcome.signal["realization_repair"]["attempted"] is True
    assert outcome.signal["realization_repair"]["succeeded"] is False
    assert ai.realization_calls == 2
    assert outcome.shadow_state["comparison"]["realization_failures"] == 1


def test_realizer_rejects_repeated_question_after_selection():
    repeated = "What does the frozen architecture evidence establish about this boundary?"
    ai = FakePlannerAI(realization_payload={"lead_in": "", "question": repeated})
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(recent_questions=(repeated,)),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert "DUPLICATES_PRIOR_QUESTION" in outcome.signal["realization_rejection_codes"]


def test_realizer_rejects_explicit_invented_evidence_reference():
    ai = FakePlannerAI(
        realization_payload={
            "lead_in": "The reviewer found PATH:invented.md.",
            "question": "What does that file prove?",
        }
    )
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert "NO_FROZEN_EVIDENCE_BASIS" in outcome.signal["realization_rejection_codes"]



def test_selector_rejects_premature_objective_synthesis():
    selector = NextQuestionSelector()
    context = planning_context()
    synthesize = CandidateNextMove(
        candidate_id="synthesize",
        move_type=CandidateMoveType.SYNTHESIZE_OBJECTIVE,
        target_outcome=ObjectiveOutcome.CURRENT_POSITION_CLEAR,
    )
    consequence = CandidateNextMove(
        candidate_id="consequence",
        move_type=CandidateMoveType.CLARIFY_CONSEQUENCE,
        target_outcome=ObjectiveOutcome.ENGINEERING_CONSEQUENCE_CLEAR,
    )

    selected, _ = selector.select(context=context, candidates=(synthesize, consequence))

    assert selected.selected_candidate_id == "consequence"
    rejected = {item.candidate_id: item for item in selected.rejected_candidates}
    assert CandidateRejectionCode.CONFLICTS_WITH_LOCKED_PURPOSE in rejected["synthesize"].rejection_codes


def test_realizer_rejects_artifact_theater_question():
    ai = FakePlannerAI(
        realization_payload={
            "lead_in": "",
            "question": "What template document should you create?",
        }
    )
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert "ARTIFACT_THEATER" in outcome.signal["realization_rejection_codes"]

def test_coach_turn_is_skipped_without_planner_or_realizer_call():
    ai = FakePlannerAI()
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(intent="stuck"),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="coach-3",
        operation="coach",
    )

    assert ai.plan_calls == 0
    assert ai.realization_calls == 0
    assert outcome.signal["status"] == "skipped"
    assert outcome.signal["reason"] == "synthetic_coach_request"


def test_planner_failure_is_nonblocking_shadow_signal():
    ai = FakePlannerAI(plan_error=RuntimeError("planner unavailable"))
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert outcome.signal["failure_stage"] == "planner"
    assert outcome.signal["error_type"] == "RuntimeError"
    assert outcome.shadow_state["comparison"]["failed_plans"] == 1


def test_realizer_failure_is_nonblocking_and_preserves_planner_usage():
    ai = FakePlannerAI(realization_error=RuntimeError("realizer unavailable"))
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert outcome.signal["failure_stage"] == "realizer"
    assert outcome.signal["error_type"] == "RuntimeError"
    assert [event["purpose"] for event in outcome.usage_events] == ["review_planning_shadow"]


def test_planner_with_no_selectable_candidates_fails_closed_without_realizer_call():
    ai = FakePlannerAI(
        plan_payload={
            "candidates": [
                {
                    "candidate_id": "bad",
                    "move_type": "TEST_EVIDENCE_BOUNDARY",
                    "target_outcome": "EVIDENCE_BOUNDARY_CLEAR",
                    "evidence_refs": ["PATH:not-in-snapshot.md"],
                    "preferred_reviewer_lens": "evidence_auditor",
                    "teaching_required": False,
                    "reason_codes": [],
                }
            ],
            "_usage": {"purpose": "review_planning_shadow"},
        }
    )
    outcome = ReviewPlanner(ai=ai).plan_turn(
        context=planning_context(),
        shadow_state=None,
        current_engine={},
        turn_sequence=3,
        client_turn_id="turn-3",
        operation="respond",
    )

    assert outcome.signal["status"] == "failed"
    assert outcome.signal["failure_stage"] == "selector"
    assert outcome.signal["error_type"] == "NoSelectableCandidate"
    assert ai.realization_calls == 0
