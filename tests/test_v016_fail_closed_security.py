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


def test_entra_exchange_rejects_identity_from_wrong_tenant(monkeypatch):
    """
    Loyola institutional identity requires both the authorized email domain
    and the exact configured Loyola Entra tenant.

    A token from another tenant must be rejected even if it presents a
    luc.edu preferred_username.
    """
    from types import SimpleNamespace

    from apps.api.app.services import auth as auth_service

    expected_tenant = "11111111-1111-1111-1111-111111111111"
    wrong_tenant = "22222222-2222-2222-2222-222222222222"

    monkeypatch.setattr(
        auth_service,
        "get_settings",
        lambda: SimpleNamespace(
            entra_tenant=expected_tenant,
            entra_client_id="test-client-id",
            entra_client_secret="test-client-secret",
            entra_redirect_uri="https://studio.example.test/auth/entra/callback",
            entra_allowed_domain="luc.edu",
        ),
    )

    class FakeTokenResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id_token": "fake-id-token"}

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakeTokenResponse()

    monkeypatch.setattr(auth_service.httpx, "Client", FakeHttpClient)

    decode_calls = []

    def fake_decode(token, *args, **kwargs):
        decode_calls.append(kwargs)

        # First call is the intentionally unverified tenant discovery.
        if kwargs.get("options") is not None:
            return {
                "tid": wrong_tenant,
            }

        # Simulate an otherwise valid Microsoft-signed identity whose email
        # appears to belong to Loyola.
        return {
            "tid": wrong_tenant,
            "nonce": "expected-nonce",
            "preferred_username": "student@luc.edu",
        }

    monkeypatch.setattr(auth_service.jwt, "decode", fake_decode)

    class FakeSigningKey:
        key = object()

    class FakeJWKClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(auth_service, "PyJWKClient", FakeJWKClient)

    try:
        auth_service.entra_exchange(
            code="authorization-code",
            expected_nonce="expected-nonce",
        )
    except Exception as exc:
        # We deliberately assert the HTTP semantics below rather than allowing
        # a generic exception to count as a security success.
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException)
        assert exc.status_code == 403
        assert "tenant" in str(exc.detail).lower()
    else:
        raise AssertionError(
            "Entra identity from a non-Loyola tenant was accepted"
        )


def test_entra_exchange_accepts_identity_from_configured_tenant(monkeypatch):
    """
    Exact tenant enforcement must preserve legitimate Loyola authentication.

    An otherwise valid Microsoft identity from the configured tenant with the
    authorized Loyola email domain and expected nonce must be accepted.
    """
    from types import SimpleNamespace

    from apps.api.app.services import auth as auth_service

    configured_tenant = "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(
        auth_service,
        "get_settings",
        lambda: SimpleNamespace(
            entra_tenant=configured_tenant,
            entra_client_id="test-client-id",
            entra_client_secret="test-client-secret",
            entra_redirect_uri="https://studio.example.test/auth/entra/callback",
            entra_allowed_domain="luc.edu",
        ),
    )

    class FakeTokenResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id_token": "fake-id-token"}

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakeTokenResponse()

    monkeypatch.setattr(auth_service.httpx, "Client", FakeHttpClient)

    def fake_decode(token, *args, **kwargs):
        # Unverified tenant discovery.
        if kwargs.get("options") is not None:
            return {
                "tid": configured_tenant,
            }

        # Verified-token result.
        return {
            "tid": configured_tenant,
            "nonce": "expected-nonce",
            "preferred_username": "student@luc.edu",
            "name": "Loyola Student",
            "sub": "configured-tenant-subject",
        }

    monkeypatch.setattr(auth_service.jwt, "decode", fake_decode)

    class FakeSigningKey:
        key = object()

    class FakeJWKClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(auth_service, "PyJWKClient", FakeJWKClient)

    claims = auth_service.entra_exchange(
        code="authorization-code",
        expected_nonce="expected-nonce",
    )

    assert claims["tid"] == configured_tenant
    assert claims["preferred_username"] == "student@luc.edu"
    assert claims["sub"] == "configured-tenant-subject"


def test_revoked_staff_assignment_invalidates_existing_staff_session():
    """
    Staff authority must come from current database state, not a stale role
    embedded in an already-issued session token.

    Once the user's last active teaching-staff assignment is revoked, the same
    still-unexpired session must no longer authorize instructor-only routes.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import CourseSection, CourseTerm, SectionEnrollment, SectionStaff, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-STAFF-REVOKE-{suffix}",
            term_label="Staff Revocation Test",
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
            display_name="Revocation Test Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"revoked-instructor-{suffix}",
            display_name="Revoked Instructor",
            role="instructor",
        )
        db.add(instructor)
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Keep a legitimate non-staff course authorization after the
        # instructor assignment is revoked. This isolates staff-role
        # revocation from complete course/session revocation.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        db.commit()

        instructor_id = instructor.id

    finally:
        db.close()

    # The session is legitimately issued while the assignment is active.
    token = create_session_token(
        instructor_id,
        f"revoked-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke the teaching-staff assignment after the session has been issued.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/instructor/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_revoked_staff_session_cannot_bind_team_repository(monkeypatch):
    """
    Revoking teaching-staff authority must immediately remove privileged
    onboarding authority from an already-issued session.

    A stale instructor token must not bypass team membership, invoke GitHub,
    create a RepositoryConnection, or change the team's authoritative
    repository binding.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        RepositoryConnection,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamSection,
        User,
    )
    from apps.api.app.routers import onboarding as onboarding_router
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    candidate_repo = f"example/stale-staff-{suffix}"

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-STALE-BIND-{suffix}",
            term_label="Stale Staff Repository Test",
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
            display_name="Stale Staff Repository Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"stale-bind-instructor-{suffix}",
            display_name="Stale Repository Instructor",
            role="instructor",
        )
        db.add(instructor)
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Repository Team",
            repo_full_name=None,
            project_name="Project not confirmed",
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

        db.commit()

        instructor_id = instructor.id
        team_id = team.id

    finally:
        db.close()

    # Session is legitimately issued while the instructor assignment is active.
    token = create_session_token(
        instructor_id,
        f"stale-bind-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke the instructor before the privileged onboarding operation.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    github_calls = []

    class TrackingEvidenceProvider:
        def head_sha(self, repo_full_name):
            github_calls.append(repo_full_name)
            return "0123456789abcdef"

    monkeypatch.setattr(
        onboarding_router,
        "GitHubEvidenceProvider",
        TrackingEvidenceProvider,
    )

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "clone_url": f"https://github.com/{candidate_repo}.git",
            "user_id": instructor_id,
        },
    )

    assert response.status_code == 404
    assert github_calls == []

    verify_db = SessionLocal()
    try:
        team = verify_db.get(Team, team_id)
        assert team.repo_full_name == ""

        connection = (
            verify_db.query(RepositoryConnection)
            .filter_by(team_id=team_id)
            .first()
        )
        assert connection is None
    finally:
        verify_db.close()


def test_revoked_staff_session_cannot_validate_finding_state():
    """
    Revoking teaching-staff authority must immediately remove privileged
    authority over the formal engineering finding record.

    A stale instructor session must not be able to mark a finding confirmed,
    corrected, or resolved after the instructor's active staff assignment has
    been revoked.
    """
    import json
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        EvidenceSnapshot,
        ReviewFindingState,
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
    finding_id = f"FINDING-{suffix}"

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-FINDING-REVOKE-{suffix}",
            term_label="Finding Revocation Test",
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
            display_name="Finding Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"finding-instructor-{suffix}",
            display_name="Finding Test Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"finding-student-{suffix}",
            display_name="Finding Test Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Finding Test Team",
            repo_full_name=f"demo/finding-revoke-{suffix}",
            project_name="Finding Revocation Test",
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

        snapshot = EvidenceSnapshot(
            team_id=team.id,
            phase_id="A1",
            source="demo",
            commit_sha=f"sha-{suffix}",
            summary_json=json.dumps(
                {
                    "findings": [
                        {
                            "id": finding_id,
                            "title": "Protected finding",
                        }
                    ]
                }
            ),
        )
        db.add(snapshot)
        db.flush()

        session = ReviewSession(
            team_id=team.id,
            user_id=student.id,
            phase_id="A1",
            mode="board_review",
            status="active",
            challenge_state_json=json.dumps(
                {
                    "evidence_snapshot_id": snapshot.id,
                }
            ),
        )
        db.add(session)
        db.commit()

        instructor_id = instructor.id
        snapshot_id = snapshot.id
        session_id = session.id

    finally:
        db.close()

    # Session is legitimately issued while staff authority is active.
    token = create_session_token(
        instructor_id,
        f"finding-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke the assignment before the formal finding-state action.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/api/v1/reviews/{session_id}/findings/{finding_id}/disposition",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "status": "confirmed",
            "rationale": "Stale staff session must not be allowed to validate this.",
            "evidence_path": "docs/protected-evidence.md",
        },
    )

    assert response.status_code == 403

    verify_db = SessionLocal()
    try:
        persisted = (
            verify_db.query(ReviewFindingState)
            .filter_by(
                snapshot_id=snapshot_id,
                finding_id=finding_id,
            )
            .first()
        )
        assert persisted is None
    finally:
        verify_db.close()


def test_revoked_staff_session_cannot_read_student_review():
    """
    Revoking teaching-staff authority must immediately remove access to
    another student's Review Room record.

    A stale instructor session must not expose the student's conversation,
    review state, turns, or evidence after the instructor's active staff
    assignment has been revoked.
    """
    import json
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        ReviewSession,
        ReviewTurn,
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
            namespace=f"TEST-REVIEW-READ-REVOKE-{suffix}",
            term_label="Review Read Revocation Test",
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
            display_name="Review Read Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"review-read-instructor-{suffix}",
            display_name="Review Read Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"review-read-student-{suffix}",
            display_name="Protected Review Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Review Team",
            repo_full_name=f"demo/review-read-{suffix}",
            project_name="Review Confidentiality Test",
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

        session = ReviewSession(
            team_id=team.id,
            user_id=student.id,
            phase_id="A1",
            mode="board_review",
            status="active",
            challenge_state_json=json.dumps(
                {
                    "challenge": {
                        "title": "Protected review",
                    },
                    "private_test_marker": "must-not-be-exposed",
                }
            ),
        )
        db.add(session)
        db.flush()

        db.add(
            ReviewTurn(
                session_id=session.id,
                sequence=1,
                actor="student",
                lens="conversation",
                content="Protected student reasoning",
                evidence_refs_json="[]",
                signals_json="{}",
            )
        )

        db.commit()

        instructor_id = instructor.id
        session_id = session.id

    finally:
        db.close()

    # Session is validly issued while the staff assignment exists.
    token = create_session_token(
        instructor_id,
        f"review-read-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke the assignment before the protected read.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(
        f"/api/v1/reviews/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "must-not-be-exposed" not in response.text
    assert "Protected student reasoning" not in response.text


def test_revoked_staff_session_cannot_complete_student_review():
    """
    Revoked staff authority must not permit mutation of another student's
    Review Room session through an already-issued staff token.

    The protected review must remain active after the denied request.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
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
            namespace=f"TEST-REVIEW-COMPLETE-REVOKE-{suffix}",
            term_label="Review Completion Revocation Test",
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
            display_name="Review Completion Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"review-complete-instructor-{suffix}",
            display_name="Review Completion Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"review-complete-student-{suffix}",
            display_name="Protected Review Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Completion Team",
            repo_full_name=f"demo/review-complete-{suffix}",
            project_name="Review Completion Test",
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

        session = ReviewSession(
            team_id=team.id,
            user_id=student.id,
            phase_id="A1",
            mode="board_review",
            status="active",
            challenge_state_json="{}",
        )
        db.add(session)

        db.commit()

        instructor_id = instructor.id
        session_id = session.id

    finally:
        db.close()

    token = create_session_token(
        instructor_id,
        f"review-complete-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke staff authority after the session token was issued.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/api/v1/reviews/{session_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

    verify_db = SessionLocal()
    try:
        persisted = verify_db.get(ReviewSession, session_id)
        assert persisted.status == "active"
        assert persisted.completed_at is None
    finally:
        verify_db.close()


def test_revoked_staff_session_cannot_read_team_evidence():
    """
    Revoking teaching-staff authority must immediately remove access to another
    team's frozen engineering evidence.

    A stale instructor token must not expose snapshot contents after the
    instructor's active section assignment has been revoked.
    """
    import json
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        EvidenceSnapshot,
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
            namespace=f"TEST-EVIDENCE-REVOKE-{suffix}",
            term_label="Evidence Revocation Test",
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
            display_name="Evidence Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"evidence-instructor-{suffix}",
            display_name="Evidence Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"evidence-student-{suffix}",
            display_name="Protected Evidence Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Evidence Team",
            repo_full_name=f"demo/evidence-revoke-{suffix}",
            project_name="Evidence Confidentiality Test",
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

        snapshot = EvidenceSnapshot(
            team_id=team.id,
            phase_id="A1",
            source="demo",
            commit_sha=f"sha-{suffix}",
            summary_json=json.dumps(
                {
                    "private_test_marker": "protected-frozen-evidence",
                    "findings": [],
                }
            ),
        )
        db.add(snapshot)

        db.commit()

        instructor_id = instructor.id
        team_id = team.id

    finally:
        db.close()

    token = create_session_token(
        instructor_id,
        f"evidence-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke staff authority after issuing the session.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/reviews/evidence/current",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "team_id": team_id,
            "phase_id": "A1",
        },
    )

    # Team-scoped resources deliberately conceal unauthorized existence.
    assert response.status_code == 404
    assert "protected-frozen-evidence" not in response.text


def test_revoked_staff_session_cannot_list_student_reviews():
    """
    Revoking teaching-staff authority must immediately remove the ability to
    enumerate another student's Review Room sessions.

    A stale instructor token must not use its embedded staff role to query
    another student's review history after the active section assignment has
    been revoked.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
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
            namespace=f"TEST-REVIEW-LIST-REVOKE-{suffix}",
            term_label="Review List Revocation Test",
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
            display_name="Review List Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"review-list-instructor-{suffix}",
            display_name="Review List Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"review-list-student-{suffix}",
            display_name="Protected Review Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Review List Team",
            repo_full_name=f"demo/review-list-{suffix}",
            project_name="Review Enumeration Test",
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

        review = ReviewSession(
            team_id=team.id,
            user_id=student.id,
            phase_id="A1",
            mode="board_review",
            status="active",
            scenario_id=f"protected-review-{suffix}",
            challenge_state_json="{}",
        )
        db.add(review)

        db.commit()

        instructor_id = instructor.id
        student_id = student.id
        review_id = review.id

    finally:
        db.close()

    # Issue the session while staff authority is legitimate.
    token = create_session_token(
        instructor_id,
        f"review-list-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke that authority before the list request.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/reviews",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "user_id": student_id,
        },
    )

    assert response.status_code == 403

    # The protected student's review identifier must not be disclosed.
    assert f'"id":{review_id}' not in response.text.replace(" ", "")


def test_revoked_staff_session_cannot_change_team_project_metadata():
    """
    Revoking teaching-staff authority must immediately remove privileged
    authority to alter another team's authoritative project metadata.

    A stale instructor token must not change either the project name or team
    name after the instructor's active section assignment has been revoked.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamSection,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    original_team_name = f"Protected Team {suffix}"
    original_project_name = f"Protected Project {suffix}"

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-PROJECT-REVOKE-{suffix}",
            term_label="Project Metadata Revocation Test",
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
            display_name="Project Metadata Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"project-instructor-{suffix}",
            display_name="Project Metadata Instructor",
            role="instructor",
        )
        db.add(instructor)
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name=original_team_name,
            repo_full_name=f"demo/project-metadata-{suffix}",
            project_name=original_project_name,
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

        db.commit()

        instructor_id = instructor.id
        team_id = team.id

    finally:
        db.close()

    # Issue the session while the instructor assignment is legitimate.
    token = create_session_token(
        instructor_id,
        f"project-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke teaching-staff authority before the metadata mutation.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.put(
        f"/api/v1/onboarding/teams/{team_id}/project",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "project_name": "Unauthorized Project Change",
            "team_name": "Unauthorized Team Rename",
        },
    )

    # Team-scoped protected resources conceal unauthorized existence.
    assert response.status_code == 404

    verify_db = SessionLocal()
    try:
        persisted = verify_db.get(Team, team_id)
        assert persisted.project_name == original_project_name
        assert persisted.name == original_team_name
    finally:
        verify_db.close()


def test_revoked_staff_session_cannot_verify_team_repository(monkeypatch):
    """
    Revoking teaching-staff authority must immediately remove privileged
    authority to verify another team's repository.

    A stale instructor token must not invoke GitHub or change repository
    verification state after the active section assignment has been revoked.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        RepositoryConnection,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamSection,
        User,
    )
    from apps.api.app.routers import onboarding as onboarding_router
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    repo_full_name = f"example/verify-protected-{suffix}"

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-VERIFY-REVOKE-{suffix}",
            term_label="Repository Verification Revocation Test",
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
            display_name="Repository Verification Revocation Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"verify-instructor-{suffix}",
            display_name="Repository Verification Instructor",
            role="instructor",
        )
        db.add(instructor)
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Protected Verification Team",
            repo_full_name=repo_full_name,
            project_name="Repository Verification Test",
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

        connection = RepositoryConnection(
            team_id=team.id,
            repo_full_name=repo_full_name,
            clone_url=f"https://github.com/{repo_full_name}.git",
            status="identified",
            github_app_installed=False,
            connected_by_user_id=instructor.id,
        )
        db.add(connection)

        db.commit()

        instructor_id = instructor.id
        team_id = team.id
        connection_id = connection.id

    finally:
        db.close()

    # Issue the session while the instructor assignment is valid.
    token = create_session_token(
        instructor_id,
        f"verify-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke teaching-staff authority before repository verification.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    github_calls = []

    class TrackingEvidenceProvider:
        def head_sha(self, requested_repo):
            github_calls.append(requested_repo)
            return "0123456789abcdef"

    monkeypatch.setattr(
        onboarding_router,
        "GitHubEvidenceProvider",
        TrackingEvidenceProvider,
    )

    response = client.post(
        f"/api/v1/onboarding/teams/{team_id}/repository/verify",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Team-scoped protected resources conceal unauthorized existence.
    assert response.status_code == 404

    # Authorization must fail before any external GitHub interaction.
    assert github_calls == []

    verify_db = SessionLocal()
    try:
        persisted = verify_db.get(RepositoryConnection, connection_id)
        assert persisted.status == "identified"
        assert persisted.verified_at is None
        assert persisted.github_app_installed is False
    finally:
        verify_db.close()


def test_revoked_staff_session_cannot_read_another_users_onboarding_context():
    """
    Revoking teaching-staff authority must immediately remove privileged
    access to another user's onboarding and institutional identity context.

    A stale instructor token must not expose student identity or onboarding
    information after the instructor's active staff assignment is revoked.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        InstitutionalIdentity,
        SectionEnrollment,
        SectionStaff,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    protected_student_id = f"STUDENT-{suffix}"
    protected_email = f"protected-{suffix}@luc.edu"

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-ONBOARDING-PRIVACY-{suffix}",
            term_label="Onboarding Privacy Revocation Test",
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
            display_name="Onboarding Privacy Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        instructor = User(
            github_login=f"privacy-instructor-{suffix}",
            display_name="Onboarding Privacy Instructor",
            role="instructor",
        )

        student = User(
            github_login=f"privacy-student-{suffix}",
            display_name="Protected Onboarding Student",
            role="student",
        )

        db.add_all([instructor, student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=instructor.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=instructor.id,
                status="active",
            )
        )

        db.add(
            InstitutionalIdentity(
                user_id=student.id,
                student_id=protected_student_id,
                institutional_email=protected_email,
            )
        )

        db.commit()

        instructor_id = instructor.id
        student_user_id = student.id

    finally:
        db.close()

    # Issue the session while teaching-staff authority is legitimate.
    token = create_session_token(
        instructor_id,
        f"privacy-instructor-{suffix}@luc.edu",
        "instructor",
    )

    # Revoke the assignment before reading another user's onboarding context.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=instructor_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(
        f"/api/v1/onboarding/users/{student_user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

    # Institutional identity information must not be disclosed.
    assert protected_student_id not in response.text
    assert protected_email not in response.text
    assert "Protected Onboarding Student" not in response.text


def test_revoked_staff_role_cannot_impersonate_team_member_when_caller_retains_team_access():
    """
    Revoking teaching-staff authority must immediately remove the ability to
    select another team member as the subject of a new review.

    If the caller independently retains legitimate team access through team
    membership, the request may still start a review, but the authenticated
    caller must become the authoritative review subject. A stale instructor
    role embedded in the session must not preserve impersonation authority.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        ReviewSession,
        SectionEnrollment,
        SectionStaff,
        Team,
        TeamMembership,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]
    authoritative_repo = f"demo/stale-start-{suffix}"

    db = SessionLocal()

    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-STALE-START-{suffix}",
            term_label="Stale Review Start Authority Test",
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
            display_name="Stale Review Start Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        caller = User(
            github_login=f"stale-start-caller-{suffix}",
            display_name="Stale Staff Caller",
            role="student",
        )

        other_student = User(
            github_login=f"stale-start-other-{suffix}",
            display_name="Other Team Student",
            role="student",
        )

        db.add_all([caller, other_student])
        db.flush()

        assignment = SectionStaff(
            section_id=section.id,
            user_id=caller.id,
            staff_role="instructor",
            is_active=True,
        )
        db.add(assignment)

        # Preserve ordinary course authorization after staff revocation so
        # this regression isolates removal of teaching-staff authority.
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=caller.id,
                status="active",
            )
        )

        # Keep this team intentionally unsectioned so the caller's independent
        # TeamMembership remains the access path after staff revocation,
        # without involving phase-release policy in this identity regression.
        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Stale Review Start Team",
            repo_full_name=authoritative_repo,
            project_name="Review Subject Integrity Test",
            current_phase="A1",
        )
        db.add(team)
        db.flush()

        db.add_all(
            [
                TeamMembership(
                    team_id=team.id,
                    user_id=caller.id,
                    responsibility_role="Engineering Contributor",
                    is_primary=True,
                ),
                TeamMembership(
                    team_id=team.id,
                    user_id=other_student.id,
                    responsibility_role="Engineering Contributor",
                    is_primary=False,
                ),
            ]
        )

        db.commit()

        caller_id = caller.id
        other_student_id = other_student.id
        team_id = team.id

    finally:
        db.close()

    # The instructor token is legitimately issued while staff authority exists.
    token = create_session_token(
        caller_id,
        f"stale-start-caller-{suffix}@luc.edu",
        "instructor",
    )

    # Remove staff authority while preserving the caller's team membership.
    db = SessionLocal()
    try:
        assignment = (
            db.query(SectionStaff)
            .filter_by(
                user_id=caller_id,
                staff_role="instructor",
            )
            .one()
        )
        assignment.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/reviews/start",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "team_id": team_id,
            "user_id": other_student_id,
            "phase_id": "A1",
            "mode": "board_review",
            "repo_full_name": authoritative_repo,
        },
    )

    # The caller still legitimately belongs to the team, so starting their
    # own review remains valid.
    assert response.status_code == 200

    session_id = response.json()["session_id"]

    verify_db = SessionLocal()
    try:
        persisted = verify_db.get(ReviewSession, session_id)

        # Current identity authority, not the stale staff role, determines
        # whose Review Room record is created.
        assert persisted.user_id == caller_id
        assert persisted.user_id != other_student_id
    finally:
        verify_db.close()


def test_logout_revokes_presented_session_against_replay():
    """
    Logout must revoke the authenticated session server-side.

    Deleting a browser cookie is insufficient: if the same session credential
    has been copied and replayed as a bearer token after logout, it must no
    longer authenticate.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        user = User(
            github_login=f"session-replay-{suffix}",
            display_name="Session Replay Student",
            role="student",
            is_active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"session-replay-{suffix}@luc.edu",
        "student",
    )

    before_logout = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert before_logout.status_code == 200
    assert before_logout.json()["authenticated"] is True

    logout = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )

    assert 300 <= logout.status_code < 400

    # Simulate replay of a credential copied before logout.
    replay = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert replay.status_code == 200
    assert replay.json()["authenticated"] is False


def test_removing_course_authorization_invalidates_existing_session():
    """
    An authentication session must remain valid only while the user retains
    current Engineering Studio course authorization.

    Removing the user's last active section enrollment after login must
    invalidate the already-issued session immediately rather than allowing the
    credential to remain authenticated until its normal expiration.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        SectionEnrollment,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-SESSION-AUTHZ-{suffix}",
            term_label="Session Authorization Revocation Test",
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
            display_name="Session Authorization Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        user = User(
            github_login=f"session-authz-{suffix}",
            display_name="Session Authorization Student",
            role="student",
            is_active=True,
        )
        db.add(user)
        db.flush()

        enrollment = SectionEnrollment(
            section_id=section.id,
            user_id=user.id,
            status="active",
        )
        db.add(enrollment)
        db.commit()

        user_id = user.id
        enrollment_id = enrollment.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"session-authz-{suffix}@luc.edu",
        "student",
    )

    before_revocation = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert before_revocation.status_code == 200
    assert before_revocation.json()["authenticated"] is True

    # Remove the user's last current course authorization while leaving the
    # underlying User record active.
    db = SessionLocal()
    try:
        enrollment = db.get(SectionEnrollment, enrollment_id)
        enrollment.status = "inactive"
        db.commit()
    finally:
        db.close()

    after_revocation = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert after_revocation.status_code == 200
    assert after_revocation.json()["authenticated"] is False


def test_revoked_session_cannot_fall_back_to_developer_identity():
    """
    Presenting an invalid or revoked credential must fail authentication.

    Development-mode convenience fallback is permitted only when no credential
    was presented. A revoked bearer token must never be transformed into the
    privileged local developer identity.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import Team, User
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        user = User(
            github_login=f"revoked-no-fallback-{suffix}",
            display_name="Revoked Session User",
            role="student",
            is_active=True,
        )
        db.add(user)

        team = Team(
            course_namespace=f"TEST-REVOKED-FALLBACK-{suffix}",
            team_key=f"team-{suffix}",
            name="Protected Revoked Session Team",
            repo_full_name="",
            project_name="Session Boundary Test",
            current_phase="A1",
        )
        db.add(team)

        db.commit()

        user_id = user.id
        team_id = team.id
    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"revoked-no-fallback-{suffix}@luc.edu",
        "student",
    )

    logout = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )

    assert 300 <= logout.status_code < 400

    # This is a protected route. The revoked credential must produce an
    # authentication failure rather than being treated as "no identity" and
    # falling through to development's privileged developer context.
    response = client.get(
        "/api/v1/reviews/evidence/current",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "team_id": team_id,
            "phase_id": "A1",
        },
    )

    assert response.status_code == 401


def test_course_authorization_revocation_permanently_invalidates_session():
    """
    Once a course-authorized session loses its final active course
    authorization, that session must never become valid again.

    Restoring the user's enrollment later must require a new authentication
    session rather than resurrecting a previously issued credential.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        SectionEnrollment,
        User,
    )
    from apps.api.app.services.auth import create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"TEST-SESSION-NONRESURRECT-{suffix}",
            term_label="Session Non-Resurrection Test",
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
            display_name="Session Non-Resurrection Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        user = User(
            github_login=f"session-nonresurrect-{suffix}",
            display_name="Session Non-Resurrection Student",
            role="student",
            is_active=True,
        )
        db.add(user)
        db.flush()

        enrollment = SectionEnrollment(
            section_id=section.id,
            user_id=user.id,
            status="active",
        )
        db.add(enrollment)
        db.commit()

        user_id = user.id
        enrollment_id = enrollment.id

    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"session-nonresurrect-{suffix}@luc.edu",
        "student",
    )

    before_revocation = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert before_revocation.status_code == 200
    assert before_revocation.json()["authenticated"] is True

    # Remove the final current course authorization.
    db = SessionLocal()
    try:
        enrollment = db.get(SectionEnrollment, enrollment_id)
        enrollment.status = "inactive"
        db.commit()
    finally:
        db.close()

    revoked = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["authenticated"] is False

    # Restore course authorization. The old credential must remain dead.
    db = SessionLocal()
    try:
        enrollment = db.get(SectionEnrollment, enrollment_id)
        enrollment.status = "active"
        db.commit()
    finally:
        db.close()

    replay_after_reauthorization = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert replay_after_reauthorization.status_code == 200
    assert replay_after_reauthorization.json()["authenticated"] is False


def test_cookie_authenticated_mutation_requires_csrf_token():
    """
    A state-changing request authenticated by the browser session cookie must
    require a valid CSRF token.

    Merely possessing/sending the HttpOnly session cookie must not be enough
    to perform a POST mutation.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import User
    from apps.api.app.services.auth import COOKIE_NAME, create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        user = User(
            github_login=f"csrf-cookie-{suffix}",
            display_name="CSRF Cookie Test User",
            role="student",
            is_active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"csrf-cookie-{suffix}@luc.edu",
        "student",
    )

    # Authenticate exactly as the production browser does: with the session
    # cookie, not an Authorization bearer header.
    client.cookies.set(COOKIE_NAME, token)

    response = client.post(
        "/auth/logout",
        follow_redirects=False,
    )

    # Cookie-authenticated mutations must fail closed without a CSRF header.
    assert response.status_code == 403

    # A rejected CSRF attempt must not revoke the underlying session.
    replay = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert replay.status_code == 200
    assert replay.json()["authenticated"] is True

    client.cookies.delete(COOKIE_NAME)


def test_cookie_authenticated_browser_can_obtain_and_use_csrf_token():
    """
    An authenticated browser session must be able to obtain its session-bound
    CSRF token through safe authenticated state and use it for a mutation.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import User
    from apps.api.app.services.auth import COOKIE_NAME, create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        user = User(
            github_login=f"csrf-valid-{suffix}",
            display_name="Valid CSRF Test User",
            role="student",
            is_active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"csrf-valid-{suffix}@luc.edu",
        "student",
    )

    client.cookies.set(COOKIE_NAME, token)

    try:
        me = client.get("/auth/me")

        assert me.status_code == 200
        body = me.json()
        assert body["authenticated"] is True
        assert isinstance(body.get("csrf_token"), str)
        assert len(body["csrf_token"]) >= 32

        logout = client.post(
            "/auth/logout",
            headers={
                "X-CSRF-Token": body["csrf_token"],
            },
            follow_redirects=False,
        )

        assert 300 <= logout.status_code < 400

        replay = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert replay.status_code == 200
        assert replay.json()["authenticated"] is False

    finally:
        client.cookies.delete(COOKIE_NAME)


def test_studio_browser_client_injects_csrf_on_same_origin_mutations():
    """
    The production Studio browser must centrally attach the session-bound
    CSRF token to same-origin state-changing fetch requests.

    This must not depend on every individual Review Room, repository, or
    instructor mutation remembering to add the header manually.
    """
    from pathlib import Path

    javascript = Path(
        "apps/api/app/static/studio.js"
    ).read_text(encoding="utf-8")

    assert "csrfToken" in javascript
    assert "X-CSRF-Token" in javascript
    assert "window.fetch" in javascript or "globalThis.fetch" in javascript
    assert "me.csrf_token" in javascript


def test_studio_csrf_fetch_wrapper_uses_document_base_uri():
    """
    The central browser fetch wrapper must resolve relative API URLs from the
    document base URI rather than window.location.

    This preserves normal production behavior and also supports the inline
    browser war-game harness, which intentionally supplies an application
    <base href> while the underlying page itself is created with set_content().
    """
    from pathlib import Path

    javascript = Path(
        "apps/api/app/static/studio.js"
    ).read_text(encoding="utf-8")

    assert "document.baseURI" in javascript


def test_application_responses_include_browser_security_headers():
    """
    Studio responses must carry a conservative browser security baseline.

    HSTS is environment-dependent and is tested separately because local
    development intentionally runs over HTTP.
    """
    response = client.get("/")

    assert response.status_code == 200

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    permissions = response.headers["Permissions-Policy"]
    assert "camera=()" in permissions
    assert "microphone=()" in permissions
    assert "geolocation=()" in permissions

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "img-src 'self' data:" in csp
    assert "connect-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp


def _set_valid_production_environment(monkeypatch):
    """Configure the minimum valid synthetic production environment for tests."""
    monkeypatch.setenv("ETIS_ENV", "production")
    monkeypatch.setenv(
        "ETIS_DATABASE_URL",
        "postgresql://etis:test-password@db.example.edu/etis",
    )
    monkeypatch.setenv(
        "ETIS_WEB_ORIGIN",
        "https://studio.example.edu",
    )
    monkeypatch.setenv(
        "ETIS_SESSION_SECRET",
        "test-production-session-secret-at-least-32-characters",
    )
    monkeypatch.setenv("ETIS_DEV_LOGIN", "false")
    monkeypatch.setenv("ETIS_AI_ENABLED", "false")

    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "test-github-client")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "test-github-secret")
    monkeypatch.setenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        "https://studio.example.edu/auth/github/callback",
    )
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "test-private-key")

    monkeypatch.setenv("ENTRA_CLIENT_ID", "test-entra-client")
    monkeypatch.setenv("ENTRA_CLIENT_SECRET", "test-entra-secret")
    monkeypatch.setenv(
        "ENTRA_REDIRECT_URI",
        "https://studio.example.edu/auth/entra/callback",
    )
    monkeypatch.setenv(
        "ENTRA_TENANT",
        "11111111-2222-3333-4444-555555555555",
    )


def test_hsts_is_enabled_in_production_but_not_development(monkeypatch):
    """
    Production responses must require HTTPS on future browser requests.

    Local development intentionally uses plain HTTP, so HSTS must not be
    emitted there.
    """
    from apps.api.app.config import get_settings

    _set_valid_production_environment(monkeypatch)
    get_settings.cache_clear()

    try:
        production = client.get("/")

        assert production.status_code == 200
        assert (
            production.headers["Strict-Transport-Security"]
            == "max-age=31536000; includeSubDomains"
        )

        monkeypatch.setenv("ETIS_ENV", "development")
        get_settings.cache_clear()

        development = client.get("/")

        assert development.status_code == 200
        assert "Strict-Transport-Security" not in development.headers

    finally:
        get_settings.cache_clear()


def test_csrf_rejection_still_includes_browser_security_headers():
    """
    Security headers must remain present even when a request is rejected
    before reaching an endpoint.

    A fail-closed CSRF response must not accidentally bypass the browser
    hardening applied to normal responses.
    """
    from uuid import uuid4

    from apps.api.app.db import SessionLocal
    from apps.api.app.models import User
    from apps.api.app.services.auth import COOKIE_NAME, create_session_token

    suffix = uuid4().hex[:10]

    db = SessionLocal()
    try:
        user = User(
            github_login=f"csrf-headers-{suffix}",
            display_name="CSRF Header Test User",
            role="student",
            is_active=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    token = create_session_token(
        user_id,
        f"csrf-headers-{suffix}@luc.edu",
        "student",
    )

    client.cookies.set(COOKIE_NAME, token)

    try:
        response = client.post(
            "/auth/logout",
            follow_redirects=False,
        )

        assert response.status_code == 403
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    finally:
        client.cookies.delete(COOKIE_NAME)


def test_auth_me_is_never_cacheable():
    """
    Authentication bootstrap data must never be cached by browsers or
    intermediaries.

    /auth/me can contain current identity, authorization context, and the
    session-bound CSRF bootstrap value for cookie-authenticated browsers.
    """
    response = client.get("/auth/me")

    assert response.status_code == 200

    cache_control = response.headers["Cache-Control"].lower()

    assert "no-store" in cache_control


def test_session_cookie_is_hardened_in_production_and_local_http_compatible_in_development(monkeypatch):
    """
    Browser session cookies must preserve the production security contract.

    Production requires Secure + HttpOnly + SameSite=Lax + Path=/ with the
    defined 12-hour lifetime. Local development intentionally runs over HTTP,
    so Secure is omitted there while the other protections remain.
    """
    from fastapi.responses import RedirectResponse

    from apps.api.app.config import get_settings
    from apps.api.app.models import User
    from apps.api.app.routers import auth as auth_router

    user = User(
        id=999999,
        github_login="cookie-contract",
        display_name="Cookie Contract",
        role="student",
        is_active=True,
    )

    monkeypatch.setattr(
        auth_router,
        "create_session_token",
        lambda *_args, **_kwargs: "test-session-token",
    )

    try:
        _set_valid_production_environment(monkeypatch)
        get_settings.cache_clear()

        production = RedirectResponse("/")
        auth_router._set_session(
            production,
            user,
            "cookie-contract@luc.edu",
        )

        prod_cookie = production.headers["set-cookie"].lower()

        assert "etis_session=test-session-token" in prod_cookie
        assert "httponly" in prod_cookie
        assert "secure" in prod_cookie
        assert "samesite=lax" in prod_cookie
        assert "path=/" in prod_cookie
        assert "max-age=43200" in prod_cookie
        assert "domain=" not in prod_cookie

        monkeypatch.setenv("ETIS_ENV", "development")
        get_settings.cache_clear()

        development = RedirectResponse("/")
        auth_router._set_session(
            development,
            user,
            "cookie-contract@luc.edu",
        )

        dev_cookie = development.headers["set-cookie"].lower()

        assert "httponly" in dev_cookie
        assert "secure" not in dev_cookie
        assert "samesite=lax" in dev_cookie
        assert "path=/" in dev_cookie
        assert "max-age=43200" in dev_cookie
        assert "domain=" not in dev_cookie

    finally:
        get_settings.cache_clear()


def test_session_cookie_policy_is_centralized_in_auth_router():
    """
    Session-cookie issuance must have one implementation point so production
    cookie protections cannot drift between authentication flows.
    """
    from pathlib import Path

    auth_router = Path(
        "apps/api/app/routers/auth.py"
    ).read_text(encoding="utf-8")

    assert auth_router.count("response.set_cookie(") == 1



def test_github_identity_link_forces_explicit_account_selection(monkeypatch):
    from urllib.parse import parse_qs, urlparse

    monkeypatch.setattr(
        auth_service,
        "get_settings",
        lambda: SimpleNamespace(
            github_oauth_client_id="test-github-client",
            github_oauth_redirect_uri=(
                "https://studio.example.edu/auth/github/callback"
            ),
        ),
    )

    url = auth_service.github_authorize_url("signed-test-state")
    query = parse_qs(urlparse(url).query)

    assert query["client_id"] == ["test-github-client"]
    assert query["state"] == ["signed-test-state"]
    assert query["prompt"] == ["select_account"]
