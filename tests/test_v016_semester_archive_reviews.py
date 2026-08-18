import json

import pytest
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
from apps.api.app.services.auth import require_section_role


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


def _archive(term_id: int):
    response = client.put(
        f"/api/v1/admin/terms/{term_id}/status?status=archived"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def _staff(section_id: int, role: str) -> int:
    db = SessionLocal()
    try:
        login = f"gate12-archive-{role}-{section_id}@luc.edu"
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
                student_id=f"staff:gate12-archive-{role}-{section_id}",
                institutional_email=login,
            )
        )
        db.add(
            SectionStaff(
                section_id=section_id,
                user_id=user.id,
                staff_role=role,
                is_active=True,
            )
        )
        db.commit()
        return user.id
    finally:
        db.close()


def _active_review(ctx, *, with_snapshot: bool = False):
    db = SessionLocal()
    try:
        state = {}

        if with_snapshot:
            snapshot = EvidenceSnapshot(
                team_id=ctx["team_id"],
                phase_id="A1",
                source="gate12-test",
                commit_sha="gate12-archive-review",
                summary_json=json.dumps(
                    {
                        "phase_id": "A1",
                        "findings": [
                            {
                                "id": "gate12-finding",
                                "title": "Gate 12 finding",
                            }
                        ],
                    }
                ),
            )
            db.add(snapshot)
            db.flush()
            state["evidence_snapshot_id"] = snapshot.id

        review = ReviewSession(
            team_id=ctx["team_id"],
            user_id=ctx["user_id"],
            phase_id="A1",
            mode="board_review",
            status="active",
            scenario_id="gate12-semester-archive",
            challenge_state_json=json.dumps(state),
        )
        db.add(review)
        db.flush()

        turn = ReviewTurn(
            session_id=review.id,
            sequence=1,
            actor="student",
            lens="conversation",
            content="This reasoning must remain in the historical record.",
            evidence_refs_json="[]",
            signals_json="{}",
        )
        db.add(turn)
        db.commit()

        return review.id, turn.id
    finally:
        db.close()


def test_archiving_term_marks_active_review_archived_incomplete_and_preserves_turns():
    ctx = _seed()
    review_id, turn_id = _active_review(ctx)

    _archive(ctx["term_id"])

    db = SessionLocal()
    try:
        review = db.get(ReviewSession, review_id)
        assert review is not None
        assert review.status == "archived_incomplete"
        assert review.completed_at is not None

        turn = db.get(ReviewTurn, turn_id)
        assert turn is not None
        assert turn.content == (
            "This reasoning must remain in the historical record."
        )
    finally:
        db.close()


def test_archived_review_cannot_later_be_completed_as_normal():
    ctx = _seed()
    review_id, _turn_id = _active_review(ctx)

    _archive(ctx["term_id"])

    response = client.post(
        f"/api/v1/reviews/{review_id}/complete"
    )

    assert response.status_code == 409

    db = SessionLocal()
    try:
        review = db.get(ReviewSession, review_id)
        assert review.status == "archived_incomplete"
    finally:
        db.close()


def test_archived_review_cannot_mutate_finding_disposition():
    ctx = _seed()
    review_id, _turn_id = _active_review(
        ctx,
        with_snapshot=True,
    )

    _archive(ctx["term_id"])

    response = client.post(
        f"/api/v1/reviews/{review_id}/findings/gate12-finding/disposition",
        json={
            "status": "deferred",
            "evidence_path": "",
            "rationale": "This mutation must not be accepted after archive.",
        },
    )

    assert response.status_code == 409


def test_archived_instructor_retains_historical_section_read_authority():
    ctx = _seed()
    instructor_id = _staff(ctx["section_id"], "instructor")

    _archive(ctx["term_id"])

    db = SessionLocal()
    try:
        role = require_section_role(
            db,
            {"uid": instructor_id, "role": "instructor"},
            ctx["section_id"],
            {"course_owner", "instructor", "ta", "reviewer"},
        )
        assert role == "instructor"
    finally:
        db.close()


@pytest.mark.parametrize("role", ["ta", "reviewer"])
def test_archived_ta_and_reviewer_do_not_retain_historical_authority(role):
    ctx = _seed()
    user_id = _staff(ctx["section_id"], role)

    _archive(ctx["term_id"])

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as excinfo:
            require_section_role(
                db,
                {"uid": user_id, "role": role},
                ctx["section_id"],
                {"course_owner", "instructor", "ta", "reviewer"},
            )

        assert excinfo.value.status_code == 403
    finally:
        db.close()
