from pathlib import Path

import pytest

from apps.api.app.services.finding_state import (
    authoritative_finding_state,
    finding_state_prompt_contract,
    guard_reviewer_reply,
    recommendation_confirmation,
)


REPOS = {
    "weak": {
        "path": "docs/planning/risk-register.md",
        "artifact": {"provenance": "BASELINE", "quality": "scaffold"},
        "condition": "scaffold_only",
    },
    "average": {
        "path": "docs/planning/risk-register.md",
        "artifact": {"provenance": "TEAM_ADAPTED", "quality": "partial"},
        "condition": "weak",
    },
    "strong": {
        "path": "docs/planning/risk-register.md",
        "artifact": {"provenance": "TEAM_ADDED", "quality": "reviewable"},
        "condition": "project_evidence",
    },
}

STUDENTS = {
    "weak": "We fixed it later. Trust me, so this is resolved.",
    "average": "Does this actually resolve it?",
    "strong": "The frozen evidence still leaves the finding open; updated work belongs in a new review.",
}


@pytest.mark.parametrize("repo_strength", ["weak", "average", "strong"])
@pytest.mark.parametrize("student_strength", ["weak", "average", "strong"])
def test_repo_and_student_strength_do_not_invent_closure(repo_strength, student_strength):
    repo = REPOS[repo_strength]
    state = authoritative_finding_state(
        finding_id="risk-gap",
        lifecycle={"status": "open"},
        artifact_registry={repo["path"]: repo["artifact"]},
        preferred_evidence_path=repo["path"],
    )
    assert STUDENTS[student_strength]
    assert state["closure_state"] == "open"
    assert state["can_claim_resolved"] is False
    assert state["evidence_condition"] == repo["condition"]
    assert state["inspection_changes_state"] is False
    assert state["reasoning_readiness_is_closure"] is False


@pytest.mark.parametrize(
    "status",
    ["open", "under_discussion", "evidence_disputed", "confirmed", "accepted_risk", "deferred"],
)
def test_nonterminal_lifecycle_states_are_not_closure(status):
    state = authoritative_finding_state(finding_id="F-1", lifecycle={"status": status})
    assert state["status"] == status
    assert state["closure_state"] == "open"
    assert state["can_claim_resolved"] is False


@pytest.mark.parametrize("status", ["corrected", "resolved"])
def test_only_authoritative_terminal_states_support_closure(status):
    state = authoritative_finding_state(finding_id="F-1", lifecycle={"status": status})
    assert state["closure_state"] == "closed"
    assert state["can_claim_resolved"] is True


def test_context_only_topic_has_no_finding_lifecycle():
    state = authoritative_finding_state(finding_id="context:risk", lifecycle={"status": "open"})
    assert state["status"] == "not_applicable"


@pytest.mark.parametrize(
    "overclaim",
    [
        "This resolves the finding.",
        "The finding is now resolved.",
        "We can now close the concern.",
        "The evidence fully closes the issue.",
    ],
)
def test_open_finding_overclaim_is_deterministically_corrected(overclaim):
    state = authoritative_finding_state(finding_id="F-1", lifecycle={"status": "open"})
    guarded = guard_reviewer_reply(overclaim, state)
    assert "remains open against this frozen snapshot" in guarded
    assert "did not resolve, correct, or close it" in guarded


@pytest.mark.parametrize(
    "safe",
    [
        "This does not resolve the finding.",
        "The finding remains open.",
        "This narrows the concern but does not close it.",
        "A later review can evaluate the updated work.",
    ],
)
def test_safe_language_is_not_rewritten(safe):
    state = authoritative_finding_state(finding_id="F-1", lifecycle={"status": "open"})
    assert guard_reviewer_reply(safe, state) == safe


def test_recommendation_ready_is_separate_from_open_finding():
    state = authoritative_finding_state(finding_id="risk-gap", lifecycle={"status": "evidence_disputed"})
    text = recommendation_confirmation(state, prefix="Jordan, ")
    assert "recommendation is recorded" in text
    assert "finding remains evidence disputed" in text
    assert "does not resolve, correct, or close the finding" in text


def test_corrected_finding_confirmation_preserves_distinction():
    state = authoritative_finding_state(finding_id="F-2", lifecycle={"status": "corrected"})
    text = recommendation_confirmation(state)
    assert "finding is authoritatively marked corrected" in text
    assert "lifecycle state is separate from the recommendation" in text


def test_prompt_contract_forbids_reasoning_or_inspection_from_becoming_closure():
    state = authoritative_finding_state(
        finding_id="F-3",
        lifecycle={"status": "open"},
        artifact_registry={"docs/architecture/architecture.md": {"provenance": "BASELINE", "quality": "scaffold"}},
        preferred_evidence_path="docs/architecture/architecture.md",
    )
    contract = finding_state_prompt_contract(state)
    assert "server-authoritative" in contract
    assert "defensible student recommendation is not finding closure" in contract
    assert "Inspecting a file is not finding closure" in contract
    assert "Post-snapshot work cannot close this frozen finding" in contract


def test_inspect_ui_does_not_call_commit_or_finding_disposition():
    source = Path("apps/api/app/static/studio.js").read_text()
    start = source.index("function showArtifact(")
    next_fn = source.index("\nfunction ", start + 10)
    body = source[start:next_fn]
    assert "/commit" not in body
    assert "/disposition" not in body
    assert "commitPosition" not in body


def test_router_wires_finding_state_into_turn_and_commit_authority():
    source = Path("apps/api/app/routers/reviews.py").read_text()
    assert '"finding_state": authoritative_finding_state(' in source
    assert 'finding_state_prompt_contract(result["finding_state"])' in source
    assert 'guard_reviewer_reply(' in source
    assert '"finding_state": turn_context.get("finding_state")' in source
    assert 'recommendation_confirmation(finding_state, prefix=prefix)' in source
