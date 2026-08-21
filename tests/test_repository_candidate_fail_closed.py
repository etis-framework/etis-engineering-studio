from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
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
    REPOSITORY_STATUS_CANDIDATE,
    REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED,
)
from apps.api.app.services.auth import create_session_token
from apps.api.app.services.github_app import GitHubOwnerResolutionError


client = TestClient(app)


def _candidate_student_team():
    client.post("/api/v1/dev/seed")

    setup = client.get("/api/v1/admin/setup").json()
    section_id = setup["terms"][0]["sections"][0]["id"]

    suffix = uuid4().hex[:10]
    student_id = f"candidate-{suffix}"

    db = SessionLocal()
    try:
        section = db.get(CourseSection, section_id)
        term = db.get(CourseTerm, section.term_id)

        user = User(
            github_login=f"luc:{student_id}",
            display_name="Candidate Repository Student",
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
                github_login=f"github-{suffix}",
                github_user_id=f"gh-{suffix}",
            )
        )

        db.add(
            SectionEnrollment(
                section_id=section_id,
                user_id=user.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"candidate-{suffix}",
            name="Candidate Repository Team",
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

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        return user.id, team.id, student_id, suffix

    finally:
        db.close()


def test_repository_nomination_records_candidate_without_authoritative_binding(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    token = create_session_token(
        user_id,
        f"{student_id}@luc.edu",
        "student",
    )

    owner_calls = []

    def resolve_owner(repo_full_name):
        owner_calls.append(repo_full_name)
        return SimpleNamespace(
            login=f"github-{suffix}",
            account_id=f"gh-{suffix}",
            owner_type="User",
        )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        resolve_owner,
    )

    repo = f"github-{suffix}/comp330-f26-team"

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "clone_url": f"https://github.com/{repo}.git",
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["status"]
        == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
    )
    assert response.json()["verified"] is False
    assert response.json()["github_app_install_url"] is None
    assert response.json()["owner_type"] == "User"
    assert response.json()["owner_login"] == f"github-{suffix}"
    assert response.json()["owner_github_account_id"] == f"gh-{suffix}"
    assert response.json()["actor_is_owner"] is True

    # Owner lookup is metadata-only; repository access is still not verified.
    assert owner_calls == [repo]

    db = SessionLocal()
    try:
        persisted_team = db.get(Team, team_id)

        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )

        # Authoritative evidence repository and project metadata remain unset.
        # Candidate nomination is not authoritative team configuration.
        assert persisted_team.repo_full_name == ""
        assert persisted_team.project_name == "Project not confirmed"

        # Candidate is retained separately.
        assert connection.repo_full_name == repo
        assert (
            connection.status
            == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        )
        assert connection.owner_type == "User"
        assert connection.owner_login == f"github-{suffix}"
        assert connection.owner_github_account_id == f"gh-{suffix}"
        assert connection.verified_at is None
        assert connection.github_app_installed is False

    finally:
        db.close()


def test_unverified_candidate_can_be_changed_without_binding_either_repository(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=f"github-{suffix}",
            account_id=f"gh-{suffix}",
            owner_type="User",
        ),
    )

    token = create_session_token(
        user_id,
        f"{student_id}@luc.edu",
        "student",
    )

    headers = {
        "Authorization": f"Bearer {token}",
    }

    first_repo = f"github-{suffix}/first-candidate"
    second_repo = f"github-{suffix}/second-candidate"

    first = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=headers,
        json={
            "clone_url": f"https://github.com/{first_repo}.git",
        },
    )

    second = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=headers,
        json={
            "clone_url": f"https://github.com/{second_repo}.git",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        second.json()["status"]
        == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
    )

    db = SessionLocal()
    try:
        persisted_team = db.get(Team, team_id)

        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )

        assert persisted_team.repo_full_name == ""
        assert connection.repo_full_name == second_repo
        assert (
            connection.status
            == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        )

    finally:
        db.close()


def test_verification_refuses_promotion_if_candidate_changes_during_github_check(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    owner_login=f"github-{suffix}"
    owner_id=f"gh-{suffix}"
    first_repo=f"{owner_login}/candidate-a"
    second_repo=f"{owner_login}/candidate-b"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=owner_login,
            account_id=owner_id,
            owner_type="User",
        ),
    )

    token=create_session_token(
        user_id,
        f"{student_id}@luc.edu",
        "student",
    )
    headers={"Authorization":f"Bearer {token}"}

    nominated=client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=headers,
        json={"clone_url":f"https://github.com/{first_repo}.git"},
    )
    assert nominated.status_code==200

    def change_candidate_while_verifying(self, repo_full_name):
        assert repo_full_name==first_repo
        concurrent=SessionLocal()
        try:
            connection=(
                concurrent.query(RepositoryConnection)
                .filter_by(team_id=team_id)
                .one()
            )
            connection.repo_full_name=second_repo
            connection.clone_url=f"https://github.com/{second_repo}.git"
            connection.status=REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
            connection.owner_type="User"
            connection.owner_login=owner_login
            connection.owner_github_account_id=owner_id
            concurrent.commit()
        finally:
            concurrent.close()
        return "abc123"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.GitHubEvidenceProvider.head_sha",
        change_candidate_while_verifying,
    )

    verified=client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=headers,
    )

    assert verified.status_code==409
    assert "candidate changed" in verified.json()["detail"].lower()

    db=SessionLocal()
    try:
        team=db.get(Team,team_id)
        connection=(
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )
        assert team.repo_full_name==""
        assert connection.repo_full_name==second_repo
        assert connection.status==REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        assert connection.verified_at is None
    finally:
        db.close()


def test_owner_resolution_failure_preserves_candidate_and_fails_closed(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    token = create_session_token(
        user_id,
        f"{student_id}@luc.edu",
        "student",
    )

    def unavailable(repo_full_name):
        raise GitHubOwnerResolutionError("GitHub unavailable")

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        unavailable,
    )

    repo = f"github-{suffix}/unresolved-candidate"

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "clone_url": f"https://github.com/{repo}.git",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == REPOSITORY_STATUS_CANDIDATE
    assert response.json()["verified"] is False
    assert response.json()["github_app_install_url"] is None
    assert response.json()["owner_type"] is None
    assert response.json()["actor_is_owner"] is None
    assert response.json()["owner_resolution_error"]

    db = SessionLocal()
    try:
        team = db.get(Team, team_id)

        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )

        assert team.repo_full_name == ""
        assert connection.repo_full_name == repo
        assert connection.status == REPOSITORY_STATUS_CANDIDATE
        assert connection.owner_type is None
        assert connection.github_app_installed is False

    finally:
        db.close()


def _set_institutional_email(user_id, email):
    db = SessionLocal()
    try:
        ident = (
            db.query(InstitutionalIdentity)
            .filter_by(user_id=user_id)
            .one()
        )
        ident.institutional_email = email
        db.commit()
    finally:
        db.close()


def test_starter_kit_requires_exact_configured_test_email(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    token = create_session_token(
        user_id,
        f"{student_id}@luc.edu",
        "student",
    )

    for configured_email in ("", f"someone-else-{suffix}@gmail.com"):
        monkeypatch.setattr(
            "apps.api.app.routers.onboarding.get_settings",
            lambda configured_email=configured_email: SimpleNamespace(
                etis_production_test_student_email=configured_email,
            ),
        )

        response = client.post(
            f"/api/v1/onboarding/teams/{team_id}/repository",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "clone_url": (
                    "https://github.com/etis-framework/"
                    "comp330-f26-starter-kit.git"
                ),
            },
        )

        assert response.status_code == 409
        assert "shared COMP 330 starter kit" in response.json()["detail"]

    db = SessionLocal()
    try:
        team = db.get(Team, team_id)
        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .first()
        )

        assert team.repo_full_name == ""
        assert connection is None

    finally:
        db.close()


def test_exact_configured_test_email_can_bind_known_starter_fixture(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    configured_email=f"production-{suffix}@example.net"
    _set_institutional_email(user_id, configured_email)

    token = create_session_token(
        user_id,
        configured_email,
        "student",
    )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            etis_production_test_student_email=configured_email.upper(),
        ),
    )

    github_reads=[]

    def public_read(self, repo_full_name):
        github_reads.append(repo_full_name)
        return "abc123"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding."
        "GitHubEvidenceProvider.head_sha",
        public_read,
    )

    def unexpected_owner_lookup(repo_full_name):
        raise AssertionError(
            "controlled starter fixture must not enter normal "
            "organization-authorization onboarding"
        )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        unexpected_owner_lookup,
    )

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "clone_url": (
                "https://github.com/etis-framework/"
                "comp330-f26-starter-kit.git"
            ),
        },
    )

    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert response.json()["status"] == "verified"
    assert response.json()["production_test_repository"] is True

    assert github_reads == [
        "etis-framework/comp330-f26-starter-kit"
    ]

    db = SessionLocal()
    try:
        team = db.get(Team, team_id)

        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )

        assert (
            team.repo_full_name
            == "etis-framework/comp330-f26-starter-kit"
        )
        assert connection.status == "verified"
        assert connection.github_app_installed is False

    finally:
        db.close()


def test_test_email_exception_does_not_bypass_normal_repo_authority(
    monkeypatch,
):
    user_id, team_id, student_id, suffix = _candidate_student_team()

    configured_email=f"production-normal-{suffix}@example.net"
    _set_institutional_email(user_id, configured_email)

    token = create_session_token(
        user_id,
        configured_email,
        "student",
    )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            etis_production_test_student_email=configured_email,
        ),
    )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=f"github-{suffix}",
            account_id=f"gh-{suffix}",
            owner_type="User",
        ),
    )

    repo=f"github-{suffix}/real-team-repository"

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "clone_url": f"https://github.com/{repo}.git",
        },
    )

    assert response.status_code == 200
    assert response.json()["verified"] is False
    assert (
        response.json()["status"]
        == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
    )

    db = SessionLocal()
    try:
        team = db.get(Team, team_id)

        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )

        # Exact test-email configuration does not make arbitrary repositories
        # authoritative.
        assert team.repo_full_name == ""
        assert connection.repo_full_name == repo
        assert (
            connection.status
            == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        )

    finally:
        db.close()
