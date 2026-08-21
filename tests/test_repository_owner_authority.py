from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
from apps.api.app.routers.onboarding import _github_app_authorization_url
from apps.api.app.models import (
    CourseSection,
    CourseTerm,
    GitHubIdentity,
    InstitutionalIdentity,
    RepositoryConnection,
    SectionEnrollment,
    Team,
    TeamMembership,
    TeamSection,
    User,
)
from apps.api.app.services.auth import create_session_token


client = TestClient(app)


def _team_with_two_linked_students():
    client.post("/api/v1/dev/seed")
    setup = client.get("/api/v1/admin/setup").json()
    section_id = setup["terms"][0]["sections"][0]["id"]
    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        section = db.get(CourseSection, section_id)
        term = db.get(CourseTerm, section.term_id)

        team = Team(
            course_namespace=term.namespace,
            team_key=f"owner-authority-{suffix}",
            name="Owner Authority Team",
            repo_full_name="",
            project_name="Project not confirmed",
            current_phase="A1",
        )
        db.add(team)
        db.flush()
        db.add(
            TeamSection(
                team_id=team.id,
                section_id=section_id,
            )
        )

        users = []

        for label in ("owner", "teammate"):
            student_id = f"{label}-{suffix}"

            user = User(
                github_login=f"luc:{student_id}",
                display_name=f"{label.title()} Student",
                role="student",
            )
            db.add(user)
            db.flush()

            db.add(
                InstitutionalIdentity(
                    user_id=user.id,
                    student_id=student_id,
                    institutional_email=f"{student_id}@luc.edu",
                )
            )

            db.add(
                GitHubIdentity(
                    user_id=user.id,
                    github_login=f"github-{label}-{suffix}",
                    github_user_id=f"gh-{label}-{suffix}",
                )
            )

            db.add(
                SectionEnrollment(
                    section_id=section_id,
                    user_id=user.id,
                    status="active",
                )
            )

            db.add(
                TeamMembership(
                    team_id=team.id,
                    user_id=user.id,
                    responsibility_role="Engineering Contributor",
                    is_primary=(label == "owner"),
                )
            )

            users.append((user.id, student_id))

        db.commit()
        return team.id, suffix, users

    finally:
        db.close()


def _token(user_id, student_id):
    return create_session_token(
        user_id,
        f"{student_id}@luc.edu",
        "student",
    )


def test_personal_repository_authorization_is_exposed_only_to_actual_owner(
    monkeypatch,
):
    team_id, suffix, users = _team_with_two_linked_students()

    (owner_id, owner_sid), (
        teammate_id,
        teammate_sid,
    ) = users

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=f"github-owner-{suffix}",
            account_id=f"gh-owner-{suffix}",
            owner_type="User",
        ),
    )

    owner_headers = {
        "Authorization": f"Bearer {_token(owner_id, owner_sid)}",
    }
    teammate_headers = {
        "Authorization": (
            f"Bearer {_token(teammate_id, teammate_sid)}"
        ),
    }

    repo = f"github-owner-{suffix}/comp330-team"

    nominated = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=owner_headers,
        json={
            "clone_url": f"https://github.com/{repo}.git",
        },
    )

    assert nominated.status_code == 200

    owner_context = client.get(
        f"/api/v1/onboarding/users/{owner_id}",
        headers=owner_headers,
    ).json()["sections"][0]["repository"]

    teammate_context = client.get(
        f"/api/v1/onboarding/users/{teammate_id}",
        headers=teammate_headers,
    ).json()["sections"][0]["repository"]

    assert (
        owner_context["owner_login"]
        == f"github-owner-{suffix}"
    )
    assert owner_context["owner_is_current_user"] is True
    assert owner_context["authorization_url"] == (
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize"
    )
    assert "install_url" not in owner_context

    assert (
        teammate_context["owner_login"]
        == f"github-owner-{suffix}"
    )
    assert teammate_context["owner_is_current_user"] is False
    assert teammate_context["authorization_url"] is None
    assert "install_url" not in teammate_context

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            github_app_slug="etis-engineering-studio"
        ),
    )

    denied = client.get(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=teammate_headers,
        follow_redirects=False,
    )

    assert denied.status_code == 403
    assert "Waiting for repository owner" in denied.json()["detail"]

    allowed = client.get(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=owner_headers,
        follow_redirects=False,
    )

    assert allowed.status_code == 303
    assert allowed.headers["location"] == (
        "https://github.com/apps/etis-engineering-studio/"
        "installations/new/permissions?"
        f"suggested_target_id=gh-owner-{suffix}"
    )
    assert "repository_ids" not in allowed.headers["location"]


def test_only_personal_repository_owner_can_promote_candidate_to_verified(
    monkeypatch,
):
    team_id, suffix, users = _team_with_two_linked_students()

    (owner_id, owner_sid), (
        teammate_id,
        teammate_sid,
    ) = users

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=f"github-owner-{suffix}",
            account_id=f"gh-owner-{suffix}",
            owner_type="User",
        ),
    )

    owner_headers = {
        "Authorization": f"Bearer {_token(owner_id, owner_sid)}",
    }
    teammate_headers = {
        "Authorization": (
            f"Bearer {_token(teammate_id, teammate_sid)}"
        ),
    }

    repo = f"github-owner-{suffix}/comp330-team"

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=owner_headers,
        json={
            "clone_url": f"https://github.com/{repo}.git",
        },
    )

    assert response.status_code == 200

    github_reads = []

    def readable(self, repo_full_name):
        github_reads.append(repo_full_name)
        return "abc123"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding."
        "GitHubEvidenceProvider.head_sha",
        readable,
    )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            github_app_id="123"
        ),
    )

    denied = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=teammate_headers,
    )

    assert denied.status_code == 403

    # Fail closed before any privileged GitHub repository read.
    assert github_reads == []

    verified = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=owner_headers,
    )

    assert verified.status_code == 200
    assert verified.json()["verified"] is True
    assert verified.json()["repo_full_name"] == repo
    assert github_reads == [repo]

    db = SessionLocal()
    try:
        team = db.get(Team, team_id)

        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )

        assert team.repo_full_name == repo
        assert connection.status == "verified"

    finally:
        db.close()

    teammate_context = client.get(
        f"/api/v1/onboarding/users/{teammate_id}",
        headers=teammate_headers,
    ).json()

    assert (
        teammate_context["onboarding"]["repository_connected"]
        is True
    )


def test_organization_repository_uses_github_native_request_and_exact_verification(
    monkeypatch,
):
    team_id, suffix, users = _team_with_two_linked_students()

    owner_id, owner_sid = users[0]

    owner_headers = {
        "Authorization": f"Bearer {_token(owner_id, owner_sid)}",
    }

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=f"course-org-{suffix}",
            account_id=f"org-{suffix}",
            owner_type="Organization",
        ),
    )

    repo = f"course-org-{suffix}/comp330-team"

    nominated = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=owner_headers,
        json={
            "clone_url": f"https://github.com/{repo}.git",
        },
    )

    assert nominated.status_code == 200

    context = client.get(
        f"/api/v1/onboarding/users/{owner_id}",
        headers=owner_headers,
    ).json()["sections"][0]["repository"]

    assert context["owner_type"] == "Organization"
    assert context["organization_approval_required"] is True
    assert context["authorization_url"] is None
    assert context["organization_request_url"] == (
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize"
    )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            github_app_slug="etis-engineering-studio",
            github_app_id="123",
        ),
    )

    requested = client.get(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=owner_headers,
        follow_redirects=False,
    )

    assert requested.status_code == 303
    assert requested.headers["location"] == (
        "https://github.com/apps/etis-engineering-studio/"
        "installations/new/permissions?"
        f"suggested_target_id=org-{suffix}"
    )
    assert "repository_ids" not in requested.headers["location"]

    github_reads = []

    def readable(self, repo_full_name):
        github_reads.append(repo_full_name)
        return "abc123"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding."
        "GitHubEvidenceProvider.head_sha",
        readable,
    )

    verified = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=owner_headers,
    )

    assert verified.status_code == 200
    assert verified.json()["verified"] is True
    assert verified.json()["repo_full_name"] == repo

    # Verification reads only the exact candidate nominated by the team.
    assert github_reads == [repo]


def test_legacy_github_identity_without_immutable_id_requires_relink(monkeypatch):
    team_id, suffix, users = _team_with_two_linked_students()
    owner_id, owner_sid = users[0]

    db = SessionLocal()
    try:
        owner_identity = (
            db.query(GitHubIdentity)
            .filter_by(user_id=owner_id)
            .one()
        )
        owner_identity.github_user_id = ""
        db.commit()
    finally:
        db.close()

    headers = {
        "Authorization": f"Bearer {_token(owner_id, owner_sid)}",
    }

    context = client.get(
        f"/api/v1/onboarding/users/{owner_id}",
        headers=headers,
    )
    assert context.status_code == 200
    payload = context.json()
    assert payload["onboarding"]["github_identity"] is False
    assert payload["onboarding"]["github_identity_relink_required"] is True
    assert payload["user"]["github_login"] is None

    # A legacy display login is not sufficient authority to nominate a new
    # repository. The user receives a direct relink path instead of being
    # treated as a fully bound GitHub owner.
    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=headers,
        json={
            "clone_url": (
                f"https://github.com/github-owner-{suffix}/comp330-team.git"
            ),
        },
    )
    assert response.status_code == 409
    assert "Reconnect your GitHub identity" in response.json()["detail"]


def test_github_app_authorization_target_fails_closed_without_owner_account_id(
    monkeypatch,
):
    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(github_app_slug="etis-engineering-studio"),
    )

    conn = SimpleNamespace(owner_github_account_id="")

    with pytest.raises(HTTPException) as exc_info:
        _github_app_authorization_url(conn)

    assert exc_info.value.status_code == 409
    assert "owner identity is not ready" in str(exc_info.value.detail).lower()
