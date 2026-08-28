from apps.api.app.services.evidence import _path_matches


def test_directory_evidence_matches_files_below_expected_directory():
    paths = {
        "docs/requirements/requirements.md",
        "docs/architecture/architecture.md",
        "src/app.py",
        "tests/test_app.py",
        ".github/workflows/ci.yml",
    }

    assert _path_matches("docs/requirements/", paths)
    assert _path_matches("docs/architecture/", paths)
    assert _path_matches("src/", paths)
    assert _path_matches("tests/", paths)
    assert _path_matches(".github/workflows/", paths)


def test_directory_evidence_does_not_match_similarly_named_directory():
    paths = {
        "docs/requirements-old/requirements.md",
        "tests-old/test_app.py",
    }

    assert not _path_matches("docs/requirements/", paths)
    assert not _path_matches("tests/", paths)


def test_file_evidence_still_requires_exact_path():
    paths = {
        "docs/planning/scope.md",
        "docs/planning/scope.md.bak",
    }

    assert _path_matches("docs/planning/scope.md", paths)
    assert not _path_matches("docs/planning/estimates.md", paths)
    assert not _path_matches("docs/planning/scope", paths)


def test_compact_evidence_package_includes_bounded_action_run_details():
    from apps.api.app.services.evidence_package import EvidencePackageBuilder

    action_runs = [
        {
            "name": f"CI {index}",
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "head_sha": f"sha-{index}",
        }
        for index in range(8)
    ]

    evidence = {
        "phase_id": "A4",
        "repo_full_name": "example/team-project",
        "commit_sha": "abc123",
        "strengths": [],
        "items": [],
        "artifacts": [],
        "repository_metrics": {
            "actions_runs": 8,
            "action_runs": action_runs,
        },
        "longitudinal": {},
    }

    challenge = {
        "title": "CI evidence",
        "finding": "Review the team's automated verification evidence.",
        "decision_question": "What does the CI evidence establish?",
        "why_now": "Construction evidence should be inspectable.",
        "evidence_refs": [],
    }

    package = EvidencePackageBuilder().build(evidence, challenge)

    assert package.github_signals["actions_runs"] == 8
    assert len(package.github_signals["actions"]) == 6
    assert package.github_signals["actions"][0]["name"] == "CI 0"
    assert package.github_signals["actions"][5]["name"] == "CI 5"
