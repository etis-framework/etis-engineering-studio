import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
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


client = TestClient(app)


def _active_review_with_staff(role: str):
    suffix = uuid4().hex[:10]
    db = SessionLocal()
    try:
        term = CourseTerm(
            course_code="COMP 330",
            namespace=f"AUTH-BOUNDARY-{role}-{suffix}",
            term_label="Authority Boundary",
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
            display_name="Authority Boundary Section",
            is_active=True,
        )
        db.add(section)
        db.flush()

        student = User(
            github_login=f"student-{suffix}",
            display_name="Boundary Student",
            role="student",
        )
        staff = User(
            github_login=f"staff-{role}-{suffix}",
            display_name=f"Boundary {role}",
            role=role,
        )
        db.add_all([student, staff])
        db.flush()

        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=student.id,
                status="active",
            )
        )
        db.add(
            SectionStaff(
                section_id=section.id,
                user_id=staff.id,
                staff_role=role,
                is_active=True,
            )
        )

        team = Team(
            course_namespace=term.namespace,
            team_key=f"team-{suffix}",
            name="Boundary Team",
            repo_full_name=f"example/repo-{suffix}",
            project_name="Boundary Project",
            current_phase="A1",
        )
        db.add(team)
        db.flush()
        db.add(TeamSection(team_id=team.id, section_id=section.id))
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
            source="authority-boundary-test",
            commit_sha=f"sha-{suffix}",
            summary_json=json.dumps({"findings": []}),
        )
        db.add(snapshot)
        db.flush()

        session = ReviewSession(
            team_id=team.id,
            user_id=student.id,
            phase_id="A1",
            mode="board_review",
            status="active",
            scenario_id=f"boundary-{suffix}",
            challenge_state_json=json.dumps(
                {"evidence_snapshot_id": snapshot.id}
            ),
        )
        db.add(session)
        db.commit()

        return {
            "section_id": section.id,
            "student_id": student.id,
            "staff_id": staff.id,
            "team_id": team.id,
            "snapshot_id": snapshot.id,
            "session_id": session.id,
            "staff_token": create_session_token(
                staff.id,
                f"staff-{role}-{suffix}@luc.edu",
                role,
            ),
        }
    finally:
        db.close()


@pytest.mark.parametrize(
    "role",
    ["course_owner", "instructor", "ta", "reviewer"],
)
def test_teaching_staff_read_access_does_not_impersonate_student_review_actions(role):
    ctx = _active_review_with_staff(role)
    headers = {"Authorization": f"Bearer {ctx['staff_token']}"}
    session_id = ctx["session_id"]

    readable = client.get(
        f"/api/v1/reviews/{session_id}",
        headers=headers,
    )
    assert readable.status_code == 200

    student_actions = [
        (
            f"/api/v1/reviews/{session_id}/clarify",
            {"question": "Staff must not ask this as the student."},
        ),
        (
            f"/api/v1/reviews/{session_id}/coach",
            {},
        ),
        (
            f"/api/v1/reviews/{session_id}/respond",
            {"response": "Staff must not answer as the student."},
        ),
        (
            f"/api/v1/reviews/{session_id}/evidence-dispute",
            {
                "path": "docs/evidence.md",
                "explanation": "Staff must not dispute as the student.",
            },
        ),
        (
            f"/api/v1/reviews/{session_id}/commit",
            None,
        ),
        (
            f"/api/v1/reviews/{session_id}/complete",
            None,
        ),
        (
            f"/api/v1/reviews/{session_id}/findings/finding-1/disposition",
            {
                "status": "deferred",
                "rationale": "Student-originated disposition",
                "evidence_path": "",
            },
        ),
    ]

    for url, payload in student_actions:
        kwargs = {"headers": headers}
        if payload is not None:
            kwargs["json"] = payload
        response = client.post(url, **kwargs)
        assert response.status_code == 403, (role, url, response.text)


@pytest.mark.parametrize("denied_role", ["ta", "reviewer"])
def test_finding_validation_is_explicitly_limited_to_instructor_or_course_owner(
    denied_role,
):
    ctx = _active_review_with_staff("instructor")
    instructor_headers = {
        "Authorization": f"Bearer {ctx['staff_token']}"
    }

    confirmed = client.post(
        f"/api/v1/reviews/{ctx['session_id']}/findings/finding-1/disposition",
        headers=instructor_headers,
        json={
            "status": "confirmed",
            "rationale": "Instructor validation is explicit and attributable.",
            "evidence_path": "docs/evidence.md",
        },
    )
    assert confirmed.status_code == 200

    db = SessionLocal()
    try:
        state = (
            db.query(ReviewFindingState)
            .filter_by(
                snapshot_id=ctx["snapshot_id"],
                finding_id="finding-1",
            )
            .one()
        )
        assert state.created_by_user_id == ctx["staff_id"]

        suffix = uuid4().hex[:8]
        denied = User(
            github_login=f"validation-{denied_role}-{suffix}",
            display_name=f"Validation {denied_role}",
            role=denied_role,
        )
        db.add(denied)
        db.flush()
        db.add(
            SectionStaff(
                section_id=ctx["section_id"],
                user_id=denied.id,
                staff_role=denied_role,
                is_active=True,
            )
        )
        db.commit()
        denied_id = denied.id
    finally:
        db.close()

    denied_token = create_session_token(
        denied_id,
        f"validation-{denied_role}@luc.edu",
        denied_role,
    )
    denied_response = client.post(
        f"/api/v1/reviews/{ctx['session_id']}/findings/finding-1/disposition",
        headers={"Authorization": f"Bearer {denied_token}"},
        json={
            "status": "corrected",
            "rationale": "Read-only staff must not validate findings.",
            "evidence_path": "docs/evidence.md",
        },
    )
    assert denied_response.status_code == 403


def test_archived_student_review_is_not_exposed_through_another_active_enrollment():
    suffix = uuid4().hex[:10]
    db = SessionLocal()
    try:
        student = User(
            github_login=f"cross-term-student-{suffix}",
            display_name="Cross Term Student",
            role="student",
        )
        db.add(student)
        db.flush()

        archived_term = CourseTerm(
            course_code="COMP 330",
            namespace=f"ARCHIVED-{suffix}",
            term_label="Archived Term",
            starts_on="2025-08-01",
            ends_on="2025-12-31",
            timezone="America/Chicago",
            status="archived",
        )
        active_term = CourseTerm(
            course_code="COMP 330",
            namespace=f"ACTIVE-{suffix}",
            term_label="Active Term",
            starts_on="2026-08-01",
            ends_on="2026-12-31",
            timezone="America/Chicago",
            status="active",
        )
        db.add_all([archived_term, active_term])
        db.flush()

        archived_section = CourseSection(
            term_id=archived_term.id,
            section_key="001",
            display_name="Archived Section",
            is_active=True,
        )
        active_section = CourseSection(
            term_id=active_term.id,
            section_key="001",
            display_name="Active Section",
            is_active=True,
        )
        db.add_all([archived_section, active_section])
        db.flush()

        db.add_all(
            [
                SectionEnrollment(
                    section_id=archived_section.id,
                    user_id=student.id,
                    status="active",
                ),
                SectionEnrollment(
                    section_id=active_section.id,
                    user_id=student.id,
                    status="active",
                ),
            ]
        )

        archived_team = Team(
            course_namespace=archived_term.namespace,
            team_key="archived-team",
            name="Archived Team",
            repo_full_name="example/archived",
            project_name="Archived Project",
            current_phase="A1",
        )
        db.add(archived_team)
        db.flush()
        db.add(
            TeamSection(
                team_id=archived_team.id,
                section_id=archived_section.id,
            )
        )
        db.add(
            TeamMembership(
                team_id=archived_team.id,
                user_id=student.id,
                responsibility_role="Engineering Contributor",
                is_primary=True,
            )
        )

        review = ReviewSession(
            team_id=archived_team.id,
            user_id=student.id,
            phase_id="A1",
            mode="board_review",
            status="completed",
            scenario_id="archived-history",
            challenge_state_json="{}",
        )
        db.add(review)
        db.commit()
        student_id = student.id
        review_id = review.id
    finally:
        db.close()

    # The active enrollment keeps the Studio session valid, but it must not
    # resurrect student access to the archived term's retained review record.
    token = create_session_token(
        student_id,
        f"cross-term-{suffix}@luc.edu",
        "student",
    )
    headers = {"Authorization": f"Bearer {token}"}

    direct = client.get(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
    )
    assert direct.status_code == 404

    listed = client.get(
        "/api/v1/reviews",
        headers=headers,
    )
    assert listed.status_code == 200
    assert all(
        row["id"] != review_id
        for row in listed.json()["sessions"]
    )
