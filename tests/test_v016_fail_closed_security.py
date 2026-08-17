from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.routers import dev as dev_router
from apps.api.app.routers import repositories as repositories_router
from apps.api.app.services import auth as auth_service


client = TestClient(app)


class _FakeEvidenceResult:
    def to_dict(self):
        return {
            "repository": "example/repository",
            "phase_id": "A1",
            "source": "test",
        }


class _FakeEvidenceProvider:
    def analyze(self, repo_full_name, phase_id):
        return _FakeEvidenceResult()


def test_dev_seed_is_unavailable_outside_development(monkeypatch):
    """
    Production must never expose the demo-data seed endpoint.

    v0.15 defect:
    /api/v1/dev/login checks ETIS_DEV_LOGIN, but /api/v1/dev/seed does not.
    """
    monkeypatch.setattr(
        dev_router,
        "get_settings",
        lambda: SimpleNamespace(
            etis_env="production",
            etis_dev_login=False,
        ),
    )

    response = client.post("/api/v1/dev/seed")

    assert response.status_code == 404


def test_repository_analysis_requires_authenticated_identity(monkeypatch):
    """
    Repository analysis reaches privileged GitHub evidence access and must
    never be callable by an anonymous production request.

    Force production auth semantics while replacing GitHub access with a
    deterministic local test double.
    """
    monkeypatch.setattr(
        auth_service,
        "get_settings",
        lambda: SimpleNamespace(
            etis_env="production",
            etis_dev_login=False,
        ),
    )
    monkeypatch.setattr(
        repositories_router,
        "GitHubEvidenceProvider",
        _FakeEvidenceProvider,
    )

    response = client.post(
        "/api/v1/repositories/analyze",
        json={
            "team_id": 999999,
            "phase_id": "A1",
            "repo_full_name": "example/repository",
        },
    )

    assert response.status_code == 401


def test_review_start_rejects_unknown_team_instead_of_using_demo_team():
    """
    Exact team identity is part of the review context.

    An invalid team_id must fail closed. It must never be silently replaced
    with the demo team because that would substitute evidence and context.
    """
    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200

    response = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": 999999,
            "phase_id": "A1",
            "user_id": seed.json()["user_id"],
            "mode": "board_review",
        },
    )

    assert response.status_code == 404


def test_review_start_rejects_unknown_user_instead_of_using_demo_student():
    """
    Exact user identity is part of the review context.

    An invalid user_id must fail closed. It must never be silently replaced
    with the seeded demo student.
    """
    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200

    response = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seed.json()["team_id"],
            "phase_id": "A1",
            "user_id": 999999,
            "mode": "board_review",
        },
    )

    assert response.status_code == 404


def test_student_cannot_analyze_another_team_repository(monkeypatch):
    """
    An authenticated student may only analyze repositories for a team to which
    the student is assigned.

    The authorization check must happen before privileged GitHub access.
    A denied request must not confirm that the other team exists.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import Team, TeamMembership, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    db = SessionLocal()

    try:
        user = User(
            github_login=f"scope-student-{suffix}",
            display_name="Scope Test Student",
            role="student",
        )
        db.add(user)
        db.flush()

        own_team = Team(
            course_namespace=f"TEST-{suffix}",
            team_key="team-own",
            name="Own Team",
            repo_full_name=f"example/own-{suffix}",
            project_name="Authorization Test",
            current_phase="A1",
        )

        other_team = Team(
            course_namespace=f"TEST-{suffix}",
            team_key="team-other",
            name="Other Team",
            repo_full_name=f"example/other-{suffix}",
            project_name="Authorization Test",
            current_phase="A1",
        )

        db.add_all([own_team, other_team])
        db.flush()

        db.add(
            TeamMembership(
                team_id=own_team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        user_id = user.id
        other_team_id = other_team.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"scope-student-{suffix}@luc.edu",
        "student",
    )

    github_calls = []

    class TrackingEvidenceProvider:
        def analyze(self, repo_full_name, phase_id):
            github_calls.append((repo_full_name, phase_id))
            return _FakeEvidenceResult()

    monkeypatch.setattr(
        repositories_router,
        "GitHubEvidenceProvider",
        TrackingEvidenceProvider,
    )

    response = client.post(
        "/api/v1/repositories/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": other_team_id,
            "phase_id": "A1",
            "repo_full_name": f"example/other-{suffix}",
        },
    )

    assert response.status_code == 404
    assert github_calls == []


def test_repository_analysis_cannot_override_authoritative_team_repository(monkeypatch):
    """
    Repository analysis is read/evaluate behavior, not repository onboarding.

    Once a team has an authoritative repository binding, a caller must not be
    able to supply another repo_full_name, cause privileged GitHub access to
    that repository, or silently rewrite the team's binding.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import Team, TeamMembership, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    authoritative_repo = f"example/authoritative-{suffix}"
    substituted_repo = f"example/substituted-{suffix}"

    db = SessionLocal()

    try:
        user = User(
            github_login=f"binding-student-{suffix}",
            display_name="Repository Binding Test Student",
            role="student",
        )
        db.add(user)
        db.flush()

        team = Team(
            course_namespace=f"TEST-BIND-{suffix}",
            team_key="team-01",
            name="Repository Binding Team",
            repo_full_name=authoritative_repo,
            project_name="Authorization Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        user_id = user.id
        team_id = team.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"binding-student-{suffix}@luc.edu",
        "student",
    )

    github_calls = []

    class TrackingEvidenceProvider:
        def analyze(self, repo_full_name, phase_id):
            github_calls.append((repo_full_name, phase_id))
            return _FakeEvidenceResult()

    monkeypatch.setattr(
        repositories_router,
        "GitHubEvidenceProvider",
        TrackingEvidenceProvider,
    )

    response = client.post(
        "/api/v1/repositories/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "phase_id": "A1",
            "repo_full_name": substituted_repo,
        },
    )

    assert response.status_code == 409
    assert github_calls == []

    verify_db = SessionLocal()
    try:
        persisted_team = verify_db.get(Team, team_id)
        assert persisted_team.repo_full_name == authoritative_repo
    finally:
        verify_db.close()


def test_student_can_analyze_own_authoritative_team_repository(monkeypatch):
    """
    Fail-closed authorization must not break legitimate repository analysis.

    An authenticated student assigned to the team may analyze the team's
    authoritative configured repository, and GitHub access must use exactly
    that persisted repository binding.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import Team, TeamMembership, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    authoritative_repo = f"example/authorized-{suffix}"

    db = SessionLocal()

    try:
        user = User(
            github_login=f"authorized-student-{suffix}",
            display_name="Authorized Repository Student",
            role="student",
        )
        db.add(user)
        db.flush()

        team = Team(
            course_namespace=f"TEST-AUTH-{suffix}",
            team_key="team-01",
            name="Authorized Team",
            repo_full_name=authoritative_repo,
            project_name="Authorization Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        user_id = user.id
        team_id = team.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"authorized-student-{suffix}@luc.edu",
        "student",
    )

    github_calls = []

    class TrackingEvidenceProvider:
        def analyze(self, repo_full_name, phase_id):
            github_calls.append((repo_full_name, phase_id))
            return _FakeEvidenceResult()

    monkeypatch.setattr(
        repositories_router,
        "GitHubEvidenceProvider",
        TrackingEvidenceProvider,
    )

    response = client.post(
        "/api/v1/repositories/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "phase_id": "A1",
            "repo_full_name": authoritative_repo,
        },
    )

    assert response.status_code == 200
    assert github_calls == [(authoritative_repo, "A1")]


def test_review_start_cannot_override_authoritative_team_repository():
    """
    Starting a review must use the team's authoritative repository binding.

    A valid team member must not be able to provide another repo_full_name,
    cause the frozen evidence snapshot to use it, or silently rebind the team.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import Team, TeamMembership, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    authoritative_repo = f"demo/authoritative-{suffix}"
    substituted_repo = f"demo/substituted-{suffix}"

    db = SessionLocal()

    try:
        user = User(
            github_login=f"review-binding-student-{suffix}",
            display_name="Review Binding Student",
            role="student",
        )
        db.add(user)
        db.flush()

        team = Team(
            course_namespace=f"TEST-REVIEW-BIND-{suffix}",
            team_key="team-01",
            name="Review Binding Team",
            repo_full_name=authoritative_repo,
            project_name="Authorization Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        user_id = user.id
        team_id = team.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"review-binding-student-{suffix}@luc.edu",
        "student",
    )

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "user_id": user_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": substituted_repo,
        },
    )

    assert response.status_code == 409

    verify_db = SessionLocal()
    try:
        persisted_team = verify_db.get(Team, team_id)
        assert persisted_team.repo_full_name == authoritative_repo
    finally:
        verify_db.close()


def test_review_start_accepts_authoritative_team_repository():
    """
    Repository-binding protection must not break legitimate Review Room use.

    A valid team member may start a review when the requested repository
    exactly matches the team's authoritative configured repository.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import Team, TeamMembership, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    authoritative_repo = f"demo/authorized-review-{suffix}"

    db = SessionLocal()

    try:
        user = User(
            github_login=f"review-authorized-student-{suffix}",
            display_name="Authorized Review Student",
            role="student",
        )
        db.add(user)
        db.flush()

        team = Team(
            course_namespace=f"TEST-REVIEW-AUTH-{suffix}",
            team_key="team-01",
            name="Authorized Review Team",
            repo_full_name=authoritative_repo,
            project_name="Authorization Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=user.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        user_id = user.id
        team_id = team.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"review-authorized-student-{suffix}@luc.edu",
        "student",
    )

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "user_id": user_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": authoritative_repo,
        },
    )

    assert response.status_code == 200

    verify_db = SessionLocal()
    try:
        persisted_team = verify_db.get(Team, team_id)
        assert persisted_team.repo_full_name == authoritative_repo
    finally:
        verify_db.close()


def test_student_review_start_cannot_impersonate_another_student():
    """
    For a student request, authenticated session identity is authoritative.

    Student A must not be able to submit Student B's user_id and cause the
    Review Room session, history, findings, or accountability to be attributed
    to Student B.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import ReviewSession, Team, TeamMembership, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    authoritative_repo = f"demo/identity-{suffix}"

    db = SessionLocal()

    try:
        student_a = User(
            github_login=f"identity-student-a-{suffix}",
            display_name="Identity Student A",
            role="student",
        )
        student_b = User(
            github_login=f"identity-student-b-{suffix}",
            display_name="Identity Student B",
            role="student",
        )
        db.add_all([student_a, student_b])
        db.flush()

        team = Team(
            course_namespace=f"TEST-IDENTITY-{suffix}",
            team_key="team-01",
            name="Identity Test Team",
            repo_full_name=authoritative_repo,
            project_name="Identity Authorization Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add_all(
            [
                TeamMembership(
                    team_id=team.id,
                    user_id=student_a.id,
                    responsibility_role="Engineering Contributor",
                    is_primary=True,
                ),
                TeamMembership(
                    team_id=team.id,
                    user_id=student_b.id,
                    responsibility_role="Engineering Contributor",
                    is_primary=False,
                ),
            ]
        )

        db.commit()

        student_a_id = student_a.id
        student_b_id = student_b.id
        team_id = team.id

    finally:
        db.close()

    token = create_session_token(
        student_a_id,
        f"identity-student-a-{suffix}@luc.edu",
        "student",
    )

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "user_id": student_b_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": authoritative_repo,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    # The API must report the authenticated student, not the supplied user_id.
    assert payload["user"]["id"] == student_a_id
    assert payload["user"]["id"] != student_b_id

    # More importantly, the persisted Review Room accountability record must
    # also belong to the authenticated student.
    verify_db = SessionLocal()
    try:
        session = verify_db.get(ReviewSession, payload["session_id"])
        assert session is not None
        assert session.user_id == student_a_id
        assert session.user_id != student_b_id
    finally:
        verify_db.close()


def test_staff_cannot_start_review_for_unassigned_section_team():
    """
    Teaching-staff authority is section-scoped.

    An instructor assigned to Section A must not be able to start a review
    against a team in Section B. Authorization must fail before protected
    Review Room evidence/context is created or exposed.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        PhaseSchedule,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamMembership,
        TeamSection,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-STAFF-SCOPE-{suffix}",
            term_label="Staff Scope Test",
            starts_on="2026-08-01",
            ends_on="2026-12-31",
            timezone="America/Chicago",
            status="active",
        )
        db.add(term)
        db.flush()

        section_a = CourseSection(
            term_id=term.id,
            section_key=f"A-{suffix}",
            display_name="Authorized Section",
            is_active=True,
        )
        section_b = CourseSection(
            term_id=term.id,
            section_key=f"B-{suffix}",
            display_name="Protected Section",
            is_active=True,
        )
        db.add_all([section_a, section_b])
        db.flush()

        # Make A1 legitimately available in the protected section so a phase
        # lock cannot hide the authorization defect we are testing.
        db.add(
            PhaseSchedule(
                section_id=section_b.id,
                phase_id="A1",
                release_override="released",
            )
        )

        instructor = User(
            github_login=f"staff-scope-instructor-{suffix}",
            display_name="Section A Instructor",
            role="instructor",
        )

        protected_student = User(
            github_login=f"staff-scope-student-{suffix}",
            display_name="Protected Section Student",
            role="student",
        )

        db.add_all([instructor, protected_student])
        db.flush()

        # Instructor has authority only in Section A.
        db.add(
            SectionStaff(
                section_id=section_a.id,
                user_id=instructor.id,
                staff_role="instructor",
                is_active=True,
            )
        )

        # Student and team belong to Section B.
        db.add(
            SectionEnrollment(
                section_id=section_b.id,
                user_id=protected_student.id,
                status="active",
            )
        )

        protected_team = Team(
            course_namespace=term.namespace,
            team_key=f"protected-{suffix}",
            name="Protected Section Team",
            repo_full_name=f"demo/staff-scope-{suffix}",
            project_name="Staff Scope Test",
            current_phase="A1",
        )
        db.add(protected_team)
        db.flush()

        db.add(
            TeamSection(
                team_id=protected_team.id,
                section_id=section_b.id,
            )
        )

        db.add(
            TeamMembership(
                team_id=protected_team.id,
                user_id=protected_student.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        instructor_id = instructor.id
        protected_student_id = protected_student.id
        protected_team_id = protected_team.id
        protected_repo = protected_team.repo_full_name

    finally:
        db.close()

    token = create_session_token(
        instructor_id,
        f"staff-scope-instructor-{suffix}@luc.edu",
        "instructor",
    )

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": protected_team_id,
            "user_id": protected_student_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": protected_repo,
        },
    )

    # Do not disclose whether a protected team exists.
    assert response.status_code == 404


def test_assigned_staff_can_start_review_for_section_team():
    """
    Section-scoped authorization must preserve legitimate teaching-staff use.

    An instructor actively assigned to the team's section may start a review
    for a student on that team.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        PhaseSchedule,
        ReviewSession,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamMembership,
        TeamSection,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-STAFF-ALLOW-{suffix}",
            term_label="Staff Allow Test",
            starts_on="2026-08-01",
            ends_on="2026-12-31",
            timezone="America/Chicago",
            status="active",
        )
        db.add(term)
        db.flush()

        section = CourseSection(
            term_id=term.id,
            section_key=f"A-{suffix}",
            display_name="Authorized Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        db.add(
            PhaseSchedule(
                section_id=section.id,
                phase_id="A1",
                release_override="released",
            )
        )

        instructor = User(
            github_login=f"staff-allow-instructor-{suffix}",
            display_name="Authorized Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"staff-allow-student-{suffix}",
            display_name="Authorized Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        db.add(
            SectionStaff(
                section_id=section.id,
                user_id=instructor.id,
                staff_role="instructor",
                is_active=True,
            )
        )

        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=student.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Authorized Staff Team",
            repo_full_name=f"demo/staff-allow-{suffix}",
            project_name="Staff Authorization Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamSection(
                team_id=team.id,
                section_id=section.id,
            )
        )

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=student.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        instructor_id = instructor.id
        student_id = student.id
        team_id = team.id
        repo = team.repo_full_name

    finally:
        db.close()

    token = create_session_token(
        instructor_id,
        f"staff-allow-instructor-{suffix}@luc.edu",
        "instructor",
    )

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "user_id": student_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": repo,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    verify_db = SessionLocal()
    try:
        session = verify_db.get(ReviewSession, payload["session_id"])
        assert session is not None
        assert session.team_id == team_id
        assert session.user_id == student_id
    finally:
        verify_db.close()


def test_staff_cannot_start_team_review_for_nonmember_student():
    """
    Authorized teaching staff may review only legitimate team/student pairings.

    Even when the staff member is assigned to the section, an active student
    who is not a member of the selected team must not be used as the review
    subject for that team.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        PhaseSchedule,
        ReviewSession,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamMembership,
        TeamSection,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-STAFF-NONMEMBER-{suffix}",
            term_label="Staff Nonmember Test",
            starts_on="2026-08-01",
            ends_on="2026-12-31",
            timezone="America/Chicago",
            status="active",
        )
        db.add(term)
        db.flush()

        section = CourseSection(
            term_id=term.id,
            section_key=f"A-{suffix}",
            display_name="Authorized Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        db.add(
            PhaseSchedule(
                section_id=section.id,
                phase_id="A1",
                release_override="released",
            )
        )

        instructor = User(
            github_login=f"staff-nonmember-instructor-{suffix}",
            display_name="Authorized Instructor",
            role="instructor",
        )

        team_student = User(
            github_login=f"staff-nonmember-team-student-{suffix}",
            display_name="Actual Team Student",
            role="student",
        )

        outsider_student = User(
            github_login=f"staff-nonmember-outsider-{suffix}",
            display_name="Nonmember Student",
            role="student",
        )

        db.add_all([instructor, team_student, outsider_student])
        db.flush()

        db.add(
            SectionStaff(
                section_id=section.id,
                user_id=instructor.id,
                staff_role="instructor",
                is_active=True,
            )
        )

        # Both students legitimately belong to the section. Only one belongs
        # to the selected team.
        db.add_all(
            [
                SectionEnrollment(
                    section_id=section.id,
                    user_id=team_student.id,
                    status="active",
                ),
                SectionEnrollment(
                    section_id=section.id,
                    user_id=outsider_student.id,
                    status="active",
                ),
            ]
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Team",
            repo_full_name=f"demo/staff-nonmember-{suffix}",
            project_name="Staff Attribution Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add(
            TeamSection(
                team_id=team.id,
                section_id=section.id,
            )
        )

        db.add(
            TeamMembership(
                team_id=team.id,
                user_id=team_student.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        db.commit()

        instructor_id = instructor.id
        outsider_id = outsider_student.id
        team_id = team.id
        repo = team.repo_full_name

    finally:
        db.close()

    token = create_session_token(
        instructor_id,
        f"staff-nonmember-instructor-{suffix}@luc.edu",
        "instructor",
    )

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "user_id": outsider_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": repo,
        },
    )

    # Do not disclose whether the supplied student is valid for another team.
    assert response.status_code == 404

    verify_db = SessionLocal()
    try:
        invalid_session = (
            verify_db.query(ReviewSession)
            .filter_by(
                team_id=team_id,
                user_id=outsider_id,
            )
            .first()
        )
        assert invalid_session is None
    finally:
        verify_db.close()


def test_dev_login_is_unavailable_outside_development(monkeypatch):
    """
    Development login must be impossible outside the development environment,
    even if ETIS_DEV_LOGIN is accidentally left enabled.

    The request must fail before demo data is seeded or any login-side database
    mutation can occur.
    """
    from types import SimpleNamespace

    from apps.api.app.routers import dev as dev_router

    monkeypatch.setattr(
        dev_router,
        "get_settings",
        lambda: SimpleNamespace(
            etis_env="production",
            etis_dev_login=True,
            etis_course_namespace="COMP330-F26",
        ),
    )

    seed_calls = []

    def forbidden_seed(db):
        seed_calls.append(True)
        raise AssertionError("ensure_demo must not run in production")

    monkeypatch.setattr(dev_router, "ensure_demo", forbidden_seed)

    response = client.post(
        "/api/v1/dev/login",
        json={
            "github_login": "production-dev-login-attempt",
            "display_name": "Production Dev Login Attempt",
            "role": "student",
            "team_key": "team-01",
        },
    )

    assert response.status_code == 404
    assert seed_calls == []
