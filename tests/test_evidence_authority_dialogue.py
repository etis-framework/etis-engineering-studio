"""Dialogue truthfulness across phases, repository maturity, and student challenges."""

import pytest

from apps.api.app.services.challenge_engine import (
    ChallengeEngine,
    blank_reasoning,
    evidence_authority_contract,
    student_report_signal,
)
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact


PHASE_SOURCE = {
    "A1": ("docs/project/launch.md", "Stakeholder, bounded scope, success measure, and decision owner were reviewed."),
    "A2": ("docs/planning/plan.md", "Estimate range, dependency, owner, and re-estimation trigger were reviewed."),
    "A3": ("docs/architecture/decision.md", "Boundary, interface, tradeoff, assumption, and review decision were recorded."),
    "A4": ("tests/test_service.py", "The team executed the manual integration check and recorded the observed result."),
    "A5": ("docs/release/acceptance.md", "Acceptance result, residual risk, and release decision were recorded."),
    "A6": ("docs/operations/runbook.md", "Restore drill, monitoring check, owner, and observed result were recorded."),
}


def artifact(path, maturity, content):
    quality = {"weak": "scaffold", "average": "partial", "strong": "reviewable"}[maturity]
    provenance = {"weak": "BASELINE", "average": "TEAM_ADAPTED", "strong": "TEAM_ADDED"}[maturity]
    if maturity == "weak":
        content = "Starter placeholder: describe the team practice here."
    elif maturity == "average":
        content = content.split(" and ")[0] + "; remaining operating details are still incomplete."
    return ArtifactFact(
        path=path,
        exists=True,
        quality=quality,
        provenance=provenance,
        content_excerpt=content,
        review_content=content,
    )


class TruthfulnessProbe:
    def __init__(self, strong=False):
        self.strong = strong
        self.reviewer_calls = []
        self.critic_calls = []

    def available(self):
        return True

    def reviewer_turn(self, system, user):
        self.reviewer_calls.append((system, user))
        # Intentionally bad drafts exercise the selective independent critic.
        reply = (
            "The finding still stands. You did not do the work."
            if not self.strong
            else "I see the file, but the finding still stands because the reviewer already found the gap."
        )
        return {
            "student_intent": "evidence_dispute" if self.strong else "reasoning",
            "understood_points": [],
            "reasoning_updates": blank_reasoning(),
            "stuck": False,
            "frustrated": False,
            "needs_direct_teaching": False,
            "response_mode": "challenge",
            "next_target": "evidence_boundary_visible",
            "reply": reply,
            "guidance_ids": [],
            "handoff_lens": None,
            "teach_back": False,
        }

    def critique_reviewer_turn(self, system, user):
        self.critic_calls.append((system, user))
        if self.strong:
            revised = (
                "You're right to challenge that interpretation. The selected frozen source records the practice, "
                "so the review interpretation should be narrowed or corrected. I would now check whether that "
                "record is sufficient for the engineering risk rather than claiming the work was absent."
            )
        else:
            revised = (
                "That may be what your team is doing now. The repository snapshot used for this review does not "
                "demonstrate the practice, so I cannot verify it from this review. Record the smallest inspectable "
                "operating result that fits the risk; you do not need to invent a canonical document."
            )
        return {"acceptable": False, "issues": ["evidence authority"], "revised_reply": revised}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("We are testing manually now.", True),
        ("Our team reviewed this yesterday.", True),
        ("I checked the restore procedure.", True),
        ("What should we test next?", False),
        ("Can you explain manual testing?", False),
    ],
)
def test_student_report_signal_is_only_a_quality_gate(text, expected):
    assert student_report_signal(text) is expected


def test_turn_contract_tracks_selected_source_without_promoting_student_claim():
    contract = evidence_authority_contract(
        "We are doing the checks manually.",
        ["FINDING:F-17", "PATH:docs/testing/manual-checks.md"],
    )
    assert "student_report=true" in contract
    assert 'selected_paths=["docs/testing/manual-checks.md"]' in contract
    assert 'selected_findings=["F-17"]' in contract
    assert "do not silently promote it to repository proof" in contract
    assert "does not prove the activity never happened" in contract
    assert "explicitly correct or narrow the REVIEW interpretation" in contract


@pytest.mark.parametrize("phase", ["A1", "A2", "A3", "A4", "A5", "A6"])
@pytest.mark.parametrize("maturity", ["weak", "average"])
def test_reported_team_practice_never_becomes_nonoccurrence_across_a1_a6(phase, maturity):
    path, content = PHASE_SOURCE[phase]
    a = artifact(path, maturity, content)
    evidence = build_snapshot(phase, "team/repo", "frozen-sha", [path], artifacts=[a])
    challenge = ChallengeEngine(ai=object()).start(phase, evidence)
    package = EvidencePackageBuilder().build(evidence.to_dict(), challenge.to_dict()).to_prompt_text()
    probe = TruthfulnessProbe(strong=False)

    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge,
        "We are doing this manually now, but we have not put the result in the repo yet.",
        blank_reasoning(),
        evidence_context=package,
        conversation_memory={},
        student_name="Alex",
    )

    assert probe.critic_calls, f"{phase}/{maturity} student report bypassed critic"
    system, _ = probe.reviewer_calls[-1]
    _, critic_user = probe.critic_calls[-1]
    assert "TURN EVIDENCE-AUTHORITY CONTRACT" in system
    assert "Bounded frozen evidence package" in critic_user
    assert "does not demonstrate the practice" in reply["text"]
    assert "you did not do" not in reply["text"].lower()
    assert "grade" not in reply["text"].lower()


@pytest.mark.parametrize("phase", ["A1", "A2", "A3", "A4", "A5", "A6"])
def test_strong_student_counterevidence_can_correct_review_interpretation_across_a1_a6(phase):
    path, content = PHASE_SOURCE[phase]
    a = artifact(path, "strong", content)
    evidence = build_snapshot(phase, "team/repo", "frozen-sha", [path], artifacts=[a])
    challenge = ChallengeEngine(ai=object()).start(phase, evidence)
    package = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), challenge.to_dict(), [f"PATH:{path}"]
    ).to_prompt_text()
    probe = TruthfulnessProbe(strong=True)

    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge,
        "I challenge that finding. This source records the practice and the observed result.",
        blank_reasoning(),
        evidence_refs=[f"PATH:{path}", f"FINDING:{challenge.id}"],
        evidence_context=package,
        conversation_memory={},
        student_name="Jordan",
    )

    assert probe.critic_calls
    _, critic_user = probe.critic_calls[-1]
    assert path in critic_user
    assert "review interpretation should be narrowed or corrected" in reply["text"]
    assert "reviewer already found" not in reply["text"].lower()


def test_post_snapshot_claim_remains_report_and_requires_new_review_for_verification():
    contract = evidence_authority_contract("We fixed it after the snapshot and tested it today.")
    assert "student_report=true" in contract
    assert "post-snapshot work requires a new review" in contract
