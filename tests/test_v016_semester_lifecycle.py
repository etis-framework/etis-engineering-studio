from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
from apps.api.app.models import (
    EvidenceSnapshot,
    InstitutionalIdentity,
    ReviewSession,
    ReviewTurn,
    SectionStaff,
    User,
)
from apps.api.app.services.auth import create_session_token, require_team_access


client = TestClient(app)


def _seed():
    seed = client.post("/api/v1/dev/seed").json()
    setup = client.get("/api/v1/admin/setup").json()
    term = setup["terms"][0]
    section = term["sections"][0]
    return {
        "user_id": seed["user_id"],
        "team_id": seed["team_id"],
        "term_id": term["id"],
        "section_id": section["id"],
    }


def _student_token(user_id: int) -> str:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        ident = (
            db.query(InstitutionalIdentity)
            .filter_by(user_id=user_id)
            .first()
        )
        assert user is not None
        login = ident.institutional_email if ident else user.github_login
    finally:
        db.close()

    return create_session_token(user_id, login, "student")


def _staff_token(
    section_id: int,
    role: str = "instructor",
) -> tuple[int, str]:
    db = SessionLocal()
    try:
        login = f"gate12-{role}-{section_id}@luc.edu"
        user = (
            db.query(User)
            .filter_by(github_login=f"staff:{login}")
            .first()
        )
        if not user:
            user = User(
                github_login=f"staff:{login}",
                display_name=f"Gate 12 {role}",
                role=role,
            )
            db.add(user)
            db.flush()
            db.add(
                InstitutionalIdentity(
                    user_id=user.id,
                    student_id=f"staff:gate12-{role}-{section_id}",
                    institutional_email=login,
                )
            )

        assignment = (
            db.query(SectionStaff)
            .filter_by(
                section_id=section_id,
                user_id=user.id,
                staff_role=role,
            )
            .first()
        )
        if not assignment:
            db.add(
                SectionStaff(
                    section_id=section_id,
                    user_id=user.id,
                    staff_role=role,
                    is_active=True,
                )
            )

        db.commit()
        user_id = user.id
    finally:
        db.close()

    return user_id, create_session_token(user_id, login, role)


def _archive(term_id: int):
    response = client.put(
        f"/api/v1/admin/terms/{term_id}/status?status=archived"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_archiving_term_revokes_existing_student_session():
    ctx = _seed()
    token = _student_token(ctx["user_id"])
    headers = {"Authorization": f"Bearer {token}"}

    before = client.get("/auth/me", headers=headers)
    assert before.status_code == 200

    _archive(ctx["term_id"])

    after = client.get("/auth/me", headers=headers)
    assert after.status_code == 200
    assert after.json()["authenticated"] is False


def test_archived_term_no_longer_supports_student_onboarding_access():
    ctx = _seed()
    token = _student_token(ctx["user_id"])
    headers = {"Authorization": f"Bearer {token}"}

    before = client.get(
        f"/api/v1/onboarding/users/{ctx['user_id']}",
        headers=headers,
    )
    assert before.status_code == 200
    assert before.json()["sections"]

    _archive(ctx["term_id"])

    after = client.get(
        f"/api/v1/onboarding/users/{ctx['user_id']}",
        headers=headers,
    )
    assert after.status_code == 401


def test_archived_term_cannot_authorize_student_team_access():
    ctx = _seed()
    _archive(ctx["term_id"])

    db = SessionLocal()
    try:
        try:
            require_team_access(
                db,
                {"uid": ctx["user_id"], "role": "student"},
                ctx["team_id"],
            )
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError(
                "Archived enrollment must not authorize current team access"
            )
    finally:
        db.close()


def test_instructor_retains_archived_read_access_but_cannot_mutate_roster():
    ctx = _seed()
    _staff_token(ctx["section_id"], "instructor")
    _archive(ctx["term_id"])

    # Archive revokes pre-existing sessions. Reauthenticate to exercise the
    # frozen historical-read-only instructor contract.
    _staff_user_id, token = _staff_token(
        ctx["section_id"],
        "instructor",
    )
    headers = {"Authorization": f"Bearer {token}"}

    readable = client.get(
        f"/api/v1/admin/sections/{ctx['section_id']}/students",
        headers=headers,
    )
    assert readable.status_code == 200

    mutation = client.post(
        f"/api/v1/admin/sections/{ctx['section_id']}/students",
        headers=headers,
        json={
            "student_id": "archived-add",
            "name": "Archived Add",
        },
    )
    assert mutation.status_code == 409


def test_archived_term_rejects_team_metadata_mutation():
    ctx = _seed()
    _staff_token(ctx["section_id"], "instructor")
    _archive(ctx["term_id"])

    _staff_user_id, token = _staff_token(
        ctx["section_id"],
        "instructor",
    )
    headers = {"Authorization": f"Bearer {token}"}

    mutation = client.put(
        f"/api/v1/onboarding/teams/{ctx['team_id']}/project",
        headers=headers,
        json={"project_name": "Must Not Change After Archive"},
    )
    assert mutation.status_code == 409


def test_archived_course_owner_is_not_global_authority_for_active_term():
    ctx = _seed()
    _staff_token(ctx["section_id"], "course_owner")

    created_term = client.post(
        "/api/v1/admin/terms",
        json={
            "namespace": "COMP330-GATE12-ACTIVE",
            "term_label": "Gate 12 Active",
            "starts_on": "2027-01-01",
            "ends_on": "2027-05-01",
            "course_code": "COMP 330",
        },
    )
    assert created_term.status_code == 200
    active_term_id = created_term.json()["id"]

    created_section = client.post(
        f"/api/v1/admin/terms/{active_term_id}/sections",
        json={
            "section_key": "001",
            "display_name": "Gate 12 Active Section",
            "meeting_pattern": "Tue/Thu",
        },
    )
    assert created_section.status_code == 200
    active_section_id = created_section.json()["id"]

    _archive(ctx["term_id"])

    # Reauthenticate the owner for historical read access to the archived
    # term. That archived assignment must not become authority over another
    # active term.
    _owner_id, owner_token = _staff_token(
        ctx["section_id"],
        "course_owner",
    )
    headers = {"Authorization": f"Bearer {owner_token}"}

    denied = client.post(
        f"/api/v1/admin/sections/{active_section_id}/students",
        headers=headers,
        json={"student_id": "cross-term", "name": "Cross Term"},
    )
    assert denied.status_code == 403


def test_archive_preserves_engineering_record_rows():
    ctx = _seed()

    db = SessionLocal()
    try:
        snapshot = EvidenceSnapshot(
            team_id=ctx["team_id"],
            phase_id="A1",
            source="gate12-test",
            commit_sha="gate12-frozen",
            summary_json='{"frozen":true}',
        )
        db.add(snapshot)
        db.flush()

        review = ReviewSession(
            team_id=ctx["team_id"],
            user_id=ctx["user_id"],
            phase_id="A1",
            mode="board_review",
            status="active",
            scenario_id="gate12-archive",
        )
        db.add(review)
        db.flush()

        turn = ReviewTurn(
            session_id=review.id,
            sequence=1,
            actor="student",
            lens="chief_architect",
            content="Preserve this historical engineering reasoning.",
            evidence_refs_json="[]",
            signals_json="{}",
        )
        db.add(turn)
        db.commit()

        snapshot_id = snapshot.id
        review_id = review.id
        turn_id = turn.id
    finally:
        db.close()

    _archive(ctx["term_id"])

    db = SessionLocal()
    try:
        assert db.get(EvidenceSnapshot, snapshot_id) is not None
        assert db.get(ReviewSession, review_id) is not None
        assert db.get(ReviewTurn, turn_id) is not None
    finally:
        db.close()
