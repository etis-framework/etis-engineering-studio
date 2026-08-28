import shutil
from pathlib import Path

import pytest

from apps.api.app.services.repository_intelligence import analyze_local_repository

BASE = Path(__file__).parent / "fixtures" / "starter_subset"
WAVE1_PHASES = ("A1", "A2")
UNRESOLVED_EVIDENCE_CATEGORIES = {
    "missing_evidence",
    "artifact_theater",
    "weak_evidence",
}


def clone(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(BASE, root)
    return root


def adapt(path: Path, text: str):
    path.write_text(
        path.read_text()
        + "\n\n## Team-specific evidence\n"
        + text
        + "\n"
    )


def write_project_evidence(path: Path, topic: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# {topic}

This artifact records project-specific engineering evidence reviewed by the
student engineering group. Alex is the primary owner and Sam is the backup
owner. The evidence was reviewed on 2026-09-15, related decisions were recorded
in GitHub, assumptions were identified, and follow-up work has an explicit
owner and verification path.

The current content reflects the group's actual engineering position rather
than an unchanged course scaffold. Material changes are reviewed and preserved
through the repository workflow so another engineer can inspect the basis for
the decision.
"""
    )


def make_mixed_profile(root: Path):
    """
    A plausible developing repository: real project work exists, but important
    Wave 1 evidence remains incomplete or scaffold-like.
    """
    adapt(
        root / "docs/team/roles.md",
        "Alex owns architecture; Sam is backup. Both acknowledged the assignment.",
    )
    adapt(
        root / "docs/team/team-charter.md",
        "The group meets Tuesday at 6 PM and records consequential decisions in GitHub.",
    )
    adapt(
        root / "docs/planning/scope.md",
        "Cycle 1 covers authenticated project setup; reporting remains out of scope.",
    )
    adapt(
        root / "docs/planning/task-plan.md",
        "Issue 12 owns repository onboarding; Alex implements and Sam reviews.",
    )
    adapt(
        root / "docs/planning/risk-register.md",
        "R-001 covers GitHub integration uncertainty; Alex owns the mitigation spike.",
    )

    # Mixed means some genuine team-authored engineering evidence exists while
    # substantial Starter Kit scaffolding and unresolved evidence remain.
    write_project_evidence(
        root / "docs/decisions/adr-001-cycle1-scope.md",
        "Cycle 1 Scope Decision",
    )


def make_strong_profile(root: Path):
    """
    A representative strong Wave 1 repository.

    Rewrite the visible fixture artifacts as genuinely project-specific
    evidence, then add the A2 artifacts intentionally absent from the starter
    subset. This keeps the test aligned to the real A1/A2 phase contracts.
    """
    for path in root.rglob("*.md"):
        write_project_evidence(path, path.stem.replace("-", " ").title())

    for relative_path, topic in (
        ("docs/planning/README.md", "Planning Evidence Map"),
        ("docs/planning/team-commitments.md", "Team Commitments"),
        ("docs/planning/re-estimation.md", "Re-estimation Triggers"),
    ):
        write_project_evidence(root / relative_path, topic)


@pytest.mark.parametrize("phase_id", WAVE1_PHASES)
def test_weak_profile_surfaces_unresolved_evidence_for_wave1_phase(
    tmp_path,
    phase_id,
):
    root = clone(tmp_path)

    result = analyze_local_repository(root, phase_id)

    assert any(
        finding["category"] in UNRESOLVED_EVIDENCE_CATEGORIES
        for finding in result["findings"]
    )


@pytest.mark.parametrize("phase_id", WAVE1_PHASES)
def test_mixed_profile_gets_credit_but_retains_unresolved_evidence(
    tmp_path,
    phase_id,
):
    root = clone(tmp_path)
    make_mixed_profile(root)

    result = analyze_local_repository(
        root,
        phase_id,
        metrics={"issue_count": 1},
    )

    assert any(
        artifact["provenance"] in {"TEAM_ADAPTED", "TEAM_ADDED"}
        for artifact in result["artifacts"]
    )
    assert any(
        finding["category"] in UNRESOLVED_EVIDENCE_CATEGORIES
        for finding in result["findings"]
    )
    assert any(
        "project-specific evidence" in strength.lower()
        for strength in result["strengths"]
    )


@pytest.mark.parametrize("phase_id", WAVE1_PHASES)
def test_strong_profile_clears_wave1_evidence_gaps(
    tmp_path,
    phase_id,
):
    root = clone(tmp_path)
    make_strong_profile(root)

    result = analyze_local_repository(
        root,
        phase_id,
        metrics={"issue_count": 4},
    )

    unresolved = [
        finding
        for finding in result["findings"]
        if finding["category"] in UNRESOLVED_EVIDENCE_CATEGORIES
    ]

    assert unresolved == []
    assert result["strengths"]
    assert any(
        artifact["provenance"] in {"TEAM_ADAPTED", "TEAM_ADDED"}
        for artifact in result["artifacts"]
    )


def test_contradictory_profile_surfaces_readiness_conflict(tmp_path):
    root = clone(tmp_path)
    adapt(root / "README.md", "A1 is complete and launch-ready.")

    result = analyze_local_repository(root, "A1")

    assert any(
        finding["category"] == "contradiction"
        for finding in result["findings"]
    )


def test_ai_can_be_disabled_without_breaking_deterministic_core(
    tmp_path,
    monkeypatch,
):
    """
    Wave 1 acceptance contract:

    AI may be disabled without breaking the deterministic Studio foundation.
    Course/phase configuration and repository evidence analysis must continue
    to work, while semantic reviewer coaching is explicitly reported as
    unavailable rather than replaced with fabricated/canned conversation.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.config import get_settings
    from apps.api.app.main import app
    from apps.api.app.services.course_model import get_phase, load_course

    monkeypatch.setenv("ETIS_AI_ENABLED", "false")
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.etis_ai_enabled is False

        course = load_course()
        assert course
        assert get_phase("A1")["expected_evidence"]
        assert get_phase("A2")["expected_evidence"]

        root = clone(tmp_path)
        make_mixed_profile(root)

        evidence = analyze_local_repository(
            root,
            "A2",
            metrics={"issue_count": 1},
        )

        assert evidence["artifacts"]
        assert evidence["findings"]
        assert evidence["strengths"]

        with TestClient(app) as client:
            health = client.get("/health")

        assert health.status_code == 200
        payload = health.json()
        assert payload["status"] == "ok"
        assert payload["semantic_coaching_ready"] is False
        assert payload["conversation_mode"] == "semantic-required-not-configured"
        assert payload["model"] is None
        assert payload["repository_model"] is None
        assert payload["critic_model"] is None
    finally:
        get_settings.cache_clear()
