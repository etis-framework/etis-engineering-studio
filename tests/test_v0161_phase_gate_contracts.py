from apps.api.app.services.course_model import get_phase


EXPECTED_EVIDENCE_PATHS = {
    "A1": [
        "README.md",
        "docs/team/team-charter.md",
        "docs/team/roles.md",
        "docs/team/working-agreements.md",
        "docs/ai/ai-policy.md",
        "docs/ai/ai-use-log.md",
        "docs/requirements/",
        "docs/planning/",
        "docs/decisions/",
    ],
    "A2": [
        "docs/planning/README.md",
        "docs/planning/scope.md",
        "docs/planning/traceability.md",
        "docs/planning/task-plan.md",
        "docs/planning/estimates.md",
        "docs/planning/risk-register.md",
        "docs/planning/schedule.md",
        "docs/planning/team-commitments.md",
        "docs/planning/re-estimation.md",
        "GitHub Issues",
        "docs/requirements/",
        "docs/decisions/",
        "docs/ai/ai-use-log.md",
    ],
    "A3": [
        "docs/architecture/README.md",
        "docs/architecture/architecture.md",
        "docs/architecture/architecture-diagram.png",
        "docs/architecture/component-responsibilities.md",
        "docs/architecture/api-contracts.md",
        "docs/architecture/data-context.md",
        "docs/decisions/",
        "docs/reviews/architecture-review.md",
        "docs/planning/",
        "docs/testing/test-strategy.md",
        "docs/ai/ai-use-log.md",
        "GitHub Issues",
        "GitHub Pull Requests",
    ],
    "A4": [
        "docs/reviews/assignment4-review-package.md",
        "src/",
        "tests/",
        "docs/testing/",
        "docs/reviews/architecture-review.md",
        "docs/planning/traceability.md",
        ".github/pull_request_template.md",
        "GitHub Issues",
        "GitHub Pull Requests",
        ".github/workflows/ci.yml",
        "docs/ai/ai-use-log.md",
        "docs/planning/risk-register.md",
        "docs/release/known-limitations.md",
    ],
    "A5": [
        "docs/release/",
        "docs/testing/",
        "docs/quality/",
        "test-evidence/",
        "docs/ai/ai-use-log.md",
        "docs/planning/risk-register.md",
        "docs/planning/traceability.md",
        "GitHub Issues",
        "GitHub Pull Requests",
    ],
    "A6": [
        "docs/release/",
        "docs/planning/",
        "docs/testing/",
        "docs/quality/",
        "docs/operations/",
        "docs/observability/",
        "docs/security/",
        "docs/ai/ai-use-log.md",
    ],
}


def test_assignment_gate_expected_evidence_contracts_are_explicit():
    for phase_id, expected_paths in EXPECTED_EVIDENCE_PATHS.items():
        phase = get_phase(phase_id)
        actual_paths = [
            item["path"]
            for item in phase["expected_evidence"]
        ]

        assert actual_paths == expected_paths, phase_id
        assert len(actual_paths) == len(set(actual_paths)), phase_id


def test_a4_contract_includes_testing_and_validation_alignment():
    phase = get_phase("A4")

    assert "ES-109 Testing & Validation" in phase["etis_alignment"]


def test_a6_contract_preserves_final_maturity_and_stewardship_judgment():
    phase = get_phase("A6")

    assert "evidence-driven maturity improvement" in phase["gate_question"]
    assert (
        "What materially improved during Cycle 2, and what evidence shows the "
        "intended risk reduction was actually achieved?"
        in phase["decisions_to_defend"]
    )
    assert (
        "How was AI-assisted final-release work independently reviewed or "
        "verified before the team trusted it?"
        in phase["decisions_to_defend"]
    )
    assert (
        "Why does the identified final repository baseline support the claims "
        "the team is making about the release?"
        in phase["decisions_to_defend"]
    )
