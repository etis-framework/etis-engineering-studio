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
    REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED,
)
from apps.api.app.services.auth import create_session_token


client = TestClient(app)


def _three_student_team():
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
            team_key=f"wargame-{suffix}",
            name="Repository Wargame Team",
            repo_full_name="",
            project_name="Project not confirmed",
            current_phase="A1",
        )
        db.add(team)
        db.flush()
        db.add(TeamSection(team_id=team.id, section_id=section_id))

        people = {}
        for index, label in enumerate(("alice", "bob", "carol"), start=1):
            student_id = f"{label}-{suffix}"
            user = User(
                github_login=f"luc:{student_id}",
                display_name=label.title(),
                role="student",
            )
            db.add(user)
            db.flush()

            github_login = f"{label}-{suffix}"
            github_user_id = f"gh-{label}-{suffix}"

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
                    github_login=github_login,
                    github_user_id=github_user_id,
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
                    is_primary=(index == 1),
                )
            )

            people[label] = {
                "user_id": user.id,
                "student_id": student_id,
                "github_login": github_login,
                "github_user_id": github_user_id,
            }

        db.commit()
        return team.id, suffix, people
    finally:
        db.close()


def _headers(person):
    token = create_session_token(
        person["user_id"],
        f'{person["student_id"]}@luc.edu',
        "student",
    )
    return {"Authorization": f"Bearer {token}"}


def _context(person):
    return client.get(
        f'/api/v1/onboarding/users/{person["user_id"]}',
        headers=_headers(person),
    ).json()


def test_alice_bob_carol_personal_repository_lifecycle_wargame(monkeypatch):
    team_id, suffix, people = _three_student_team()
    alice, bob, carol = (
        people["alice"],
        people["bob"],
        people["carol"],
    )

    repo = f'{alice["github_login"]}/team-project'

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=alice["github_login"],
            account_id=alice["github_user_id"],
            owner_type="User",
        ),
    )

    # Bob may nominate Alice's repository, but nomination is not authority.
    nominated = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=_headers(bob),
        json={"clone_url": f"https://github.com/{repo}.git"},
    )

    assert nominated.status_code == 200
    assert (
        nominated.json()["status"]
        == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
    )
    assert nominated.json()["actor_is_owner"] is False

    contexts = {name: _context(person) for name, person in people.items()}

    for context in contexts.values():
        assert context["onboarding"]["repository_connected"] is False
        assert context["sections"][0]["team"]["repo_full_name"] == ""
        assert context["sections"][0]["repository"]["repo_full_name"] == repo

    alice_repo = contexts["alice"]["sections"][0]["repository"]
    bob_repo = contexts["bob"]["sections"][0]["repository"]
    carol_repo = contexts["carol"]["sections"][0]["repository"]

    assert alice_repo["owner_is_current_user"] is True
    assert alice_repo["authorization_url"]
    assert bob_repo["owner_is_current_user"] is False
    assert bob_repo["authorization_url"] is None
    assert carol_repo["owner_is_current_user"] is False
    assert carol_repo["authorization_url"] is None

    for context in contexts.values():
        members = context["sections"][0]["team"]["members"]
        marked = [m for m in members if m["repository_owner"]]
        assert len(marked) == 1
        assert marked[0]["github_login"] == alice["github_login"]

    github_reads = []

    def should_not_read(self, repo_full_name):
        github_reads.append(repo_full_name)
        raise AssertionError("non-owner reached privileged repository read")

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.GitHubEvidenceProvider.head_sha",
        should_not_read,
    )

    # Bob and Carol cannot authorize or verify Alice's personal repository.
    for person in (bob, carol):
        denied_authorize = client.get(
            f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
            headers=_headers(person),
            follow_redirects=False,
        )
        assert denied_authorize.status_code == 403

        denied_verify = client.post(
            f"/api/v1/onboarding/teams/{team_id}/repository/verify",
            headers=_headers(person),
        )
        assert denied_verify.status_code == 403

    assert github_reads == []

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            github_app_slug="etis-engineering-studio",
            github_app_id="123",
        ),
    )

    # GET navigation is deliberately side-effect free. Browser prefetch or a
    # copied authorization URL must not persist an "authorization started"
    # transition.
    authorized = client.get(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=_headers(alice),
        follow_redirects=False,
    )
    assert authorized.status_code == 303
    assert authorized.headers["location"] == (
        "https://github.com/apps/etis-engineering-studio/"
        "installations/new/permissions?"
        f"suggested_target_id={alice['github_user_id']}"
    )
    assert "repository_ids" not in authorized.headers["location"]

    for person in (alice, bob, carol):
        repo_context = _context(person)["sections"][0]["repository"]
        assert repo_context["authorization_started"] is False
        assert repo_context["authorization_requested_at"] is None

    # Alice explicitly performs Step 1. Only this POST may persist the
    # team-wide authorization-started state.
    started = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=_headers(alice),
    )
    assert started.status_code == 200
    assert started.json()["authorization_url"] == (
        "https://github.com/apps/etis-engineering-studio/"
        "installations/new/permissions?"
        f"suggested_target_id={alice['github_user_id']}"
    )
    assert started.json()["authorization_requested_at"]

    for person in (alice, bob, carol):
        repo_context = _context(person)["sections"][0]["repository"]
        assert repo_context["authorization_started"] is True
        assert repo_context["authorization_requested_at"]

    # Step 2 before GitHub access exists fails closed and preserves candidate.
    def unavailable(self, repo_full_name):
        assert repo_full_name == repo
        raise RuntimeError(
            "ETIS Engineering Studio GitHub App is not installed for this repository"
        )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.GitHubEvidenceProvider.head_sha",
        unavailable,
    )

    not_ready = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=_headers(alice),
    )
    assert not_ready.status_code == 502
    assert "Repository access is not ready" in not_ready.json()["detail"]

    db = SessionLocal()
    try:
        team = db.get(Team, team_id)
        connection = (
            db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .one()
        )
        assert team.repo_full_name == ""
        assert (
            connection.status
            == REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        )
    finally:
        db.close()

    # Once GitHub grants exact-repository access, Alice can verify it.
    reads = []

    def readable(self, repo_full_name):
        reads.append(repo_full_name)
        return "abc123"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.GitHubEvidenceProvider.head_sha",
        readable,
    )

    verified = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=_headers(alice),
    )
    assert verified.status_code == 200
    assert reads == [repo]

    # Verification is inherited by every teammate; nobody repeats setup.
    for person in (alice, bob, carol):
        context = _context(person)
        assert context["onboarding"]["repository_connected"] is True
        assert context["sections"][0]["team"]["repo_full_name"] == repo
        assert context["sections"][0]["repository"]["status"] == "verified"

    # A teammate cannot silently replace a verified team repository.
    replacement = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=_headers(bob),
        json={
            "clone_url": (
                f'https://github.com/{bob["github_login"]}/replacement.git'
            )
        },
    )
    assert replacement.status_code == 409
    assert "instructor must replace it" in replacement.json()["detail"].lower()


def test_wrong_linked_account_has_no_owner_authority_and_candidate_can_be_fixed(
    monkeypatch,
):
    team_id, suffix, people = _three_student_team()
    alice, bob = people["alice"], people["bob"]

    wrong_owner_login = f"alice-other-account-{suffix}"
    wrong_owner_id = f"gh-alice-other-{suffix}"

    def resolve(repo_full_name):
        owner_login = repo_full_name.split("/", 1)[0]
        if owner_login == wrong_owner_login:
            return SimpleNamespace(
                login=wrong_owner_login,
                account_id=wrong_owner_id,
                owner_type="User",
            )
        return SimpleNamespace(
            login=alice["github_login"],
            account_id=alice["github_user_id"],
            owner_type="User",
        )

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        resolve,
    )

    wrong_repo = f"{wrong_owner_login}/team-project"

    nominated = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=_headers(bob),
        json={"clone_url": f"https://github.com/{wrong_repo}.git"},
    )
    assert nominated.status_code == 200

    alice_context = _context(alice)
    repo_context = alice_context["sections"][0]["repository"]
    members = alice_context["sections"][0]["team"]["members"]

    assert repo_context["owner_login"] == wrong_owner_login
    assert repo_context["owner_is_current_user"] is False
    assert repo_context["authorization_url"] is None
    assert not any(member["repository_owner"] for member in members)
    assert alice_context["sections"][0]["team"]["repo_full_name"] == ""

    denied = client.get(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=_headers(alice),
        follow_redirects=False,
    )
    assert denied.status_code == 403

    # Any teammate may correct the unverified candidate. Old authority state
    # must disappear and Alice should immediately become the recognized owner.
    corrected_repo = f'{alice["github_login"]}/team-project'
    corrected = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=_headers(bob),
        json={"clone_url": f"https://github.com/{corrected_repo}.git"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["owner_login"] == alice["github_login"]

    corrected_alice = _context(alice)
    corrected_repo_context = corrected_alice["sections"][0]["repository"]
    assert corrected_repo_context["repo_full_name"] == corrected_repo
    assert corrected_repo_context["owner_is_current_user"] is True
    assert corrected_repo_context["authorization_started"] is False
    assert corrected_repo_context["authorization_requested_at"] is None
    assert corrected_alice["sections"][0]["team"]["repo_full_name"] == ""


def test_organization_repository_request_and_verification_are_team_wide(
    monkeypatch,
):
    team_id, suffix, people = _three_student_team()
    bob, carol = people["bob"], people["carol"]

    org_login = f"course-org-{suffix}"
    org_id = f"org-{suffix}"
    repo = f"{org_login}/team-project"

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.repository_owner_identity",
        lambda repo_full_name: SimpleNamespace(
            login=org_login,
            account_id=org_id,
            owner_type="Organization",
        ),
    )
    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.get_settings",
        lambda: SimpleNamespace(
            github_app_slug="etis-engineering-studio",
            github_app_id="123",
        ),
    )

    nominated = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers=_headers(bob),
        json={"clone_url": f"https://github.com/{repo}.git"},
    )
    assert nominated.status_code == 200

    # Carol may launch GitHub's native organization request flow; ETIS does
    # not claim that Carol, Bob, or the instructor has organization authority.
    # Compatibility GET navigation is side-effect free.
    requested = client.get(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=_headers(carol),
        follow_redirects=False,
    )
    assert requested.status_code == 303
    assert requested.headers["location"] == (
        "https://github.com/apps/etis-engineering-studio/"
        "installations/new/permissions?"
        f"suggested_target_id={org_id}"
    )
    assert "repository_ids" not in requested.headers["location"]

    for person in people.values():
        context = _context(person)
        repo_context = context["sections"][0]["repository"]
        assert repo_context["owner_type"] == "Organization"
        assert repo_context["organization_approval_required"] is True
        assert repo_context["authorization_started"] is False
        assert context["onboarding"]["repository_connected"] is False

    started = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/authorize",
        headers=_headers(carol),
    )
    assert started.status_code == 200
    assert started.json()["authorization_url"] == (
        "https://github.com/apps/etis-engineering-studio/"
        "installations/new/permissions?"
        f"suggested_target_id={org_id}"
    )

    for person in people.values():
        context = _context(person)
        repo_context = context["sections"][0]["repository"]
        assert repo_context["authorization_started"] is True
        assert repo_context["authorization_requested_at"]

    def unavailable(self, repo_full_name):
        raise RuntimeError("organization approval is still pending")

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.GitHubEvidenceProvider.head_sha",
        unavailable,
    )

    pending = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=_headers(bob),
    )
    assert pending.status_code == 502

    monkeypatch.setattr(
        "apps.api.app.routers.onboarding.GitHubEvidenceProvider.head_sha",
        lambda self, repo_full_name: "abc123",
    )

    verified = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers=_headers(carol),
    )
    assert verified.status_code == 200

    for person in people.values():
        context = _context(person)
        assert context["onboarding"]["repository_connected"] is True
        assert context["sections"][0]["team"]["repo_full_name"] == repo
