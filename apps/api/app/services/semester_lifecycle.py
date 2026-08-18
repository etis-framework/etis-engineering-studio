from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    AuthSession,
    CourseSection,
    CourseTerm,
    ReviewSession,
    SectionEnrollment,
    SectionStaff,
    TeamSection,
)


ACTIVE_TERM_STATUS = "active"
MUTABLE_TERM_STATUSES = {"setup", "active"}
ARCHIVED_TERM_STATUS = "archived"
ARCHIVED_READ_STAFF_ROLES = {"course_owner", "instructor"}


def _section_and_term(
    db: Session,
    section_id: int,
) -> tuple[CourseSection | None, CourseTerm | None]:
    section = db.get(CourseSection, section_id)
    if not section:
        return None, None
    return section, db.get(CourseTerm, section.term_id)


def _team_section_id(db: Session, team_id: int) -> int | None:
    link = (
        db.query(TeamSection)
        .filter_by(team_id=team_id)
        .first()
    )
    return link.section_id if link else None


def term_is_operational(term: CourseTerm | None) -> bool:
    return bool(term and term.status == ACTIVE_TERM_STATUS)


def term_is_mutable(term: CourseTerm | None) -> bool:
    return bool(term and term.status in MUTABLE_TERM_STATUSES)


def require_term_mutable(db: Session, term_id: int) -> CourseTerm:
    term = db.get(CourseTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    if not term_is_mutable(term):
        raise HTTPException(
            status_code=409,
            detail="Archived terms are read-only",
        )
    return term


def require_section_mutable(
    db: Session,
    section_id: int,
) -> CourseSection:
    section, term = _section_and_term(db, section_id)
    if not section or not term:
        raise HTTPException(status_code=404, detail="Section not found")
    if not term_is_mutable(term):
        raise HTTPException(
            status_code=409,
            detail="Archived terms are read-only",
        )
    return section


def require_team_mutable(db: Session, team_id: int) -> None:
    section_id = _team_section_id(db, team_id)
    if section_id is None:
        # Legacy development fixtures may contain an unbound team. There is no
        # semester lifecycle to enforce until the team is section-bound.
        return
    require_section_mutable(db, section_id)


def active_student_enrollments(
    db: Session,
    user_id: int,
) -> list[SectionEnrollment]:
    rows = (
        db.query(SectionEnrollment, CourseSection, CourseTerm)
        .join(
            CourseSection,
            CourseSection.id == SectionEnrollment.section_id,
        )
        .join(
            CourseTerm,
            CourseTerm.id == CourseSection.term_id,
        )
        .filter(
            SectionEnrollment.user_id == user_id,
            SectionEnrollment.status == "active",
            CourseSection.is_active.is_(True),
            CourseTerm.status == ACTIVE_TERM_STATUS,
        )
        .all()
    )
    return [enrollment for enrollment, _section, _term in rows]


def active_student_section_ids(
    db: Session,
    user_id: int,
) -> set[int]:
    return {
        enrollment.section_id
        for enrollment in active_student_enrollments(db, user_id)
    }


def student_has_active_section_access(
    db: Session,
    user_id: int,
    section_id: int,
) -> bool:
    return (
        db.query(SectionEnrollment)
        .join(
            CourseSection,
            CourseSection.id == SectionEnrollment.section_id,
        )
        .join(
            CourseTerm,
            CourseTerm.id == CourseSection.term_id,
        )
        .filter(
            SectionEnrollment.user_id == user_id,
            SectionEnrollment.section_id == section_id,
            SectionEnrollment.status == "active",
            CourseSection.is_active.is_(True),
            CourseTerm.status == ACTIVE_TERM_STATUS,
        )
        .first()
        is not None
    )


def valid_staff_assignments(
    db: Session,
    user_id: int,
) -> list[SectionStaff]:
    rows = (
        db.query(SectionStaff, CourseSection, CourseTerm)
        .join(
            CourseSection,
            CourseSection.id == SectionStaff.section_id,
        )
        .join(
            CourseTerm,
            CourseTerm.id == CourseSection.term_id,
        )
        .filter(
            SectionStaff.user_id == user_id,
            SectionStaff.is_active.is_(True),
        )
        .all()
    )

    valid = []
    for assignment, section, term in rows:
        if term.status in MUTABLE_TERM_STATUSES:
            if section.is_active:
                valid.append(assignment)
            continue

        if (
            term.status == ARCHIVED_TERM_STATUS
            and assignment.staff_role in ARCHIVED_READ_STAFF_ROLES
        ):
            valid.append(assignment)

    return valid


def staff_role_for_section(
    db: Session,
    user_id: int | None,
    section_id: int,
) -> str | None:
    if not user_id:
        return None

    section, term = _section_and_term(db, section_id)
    if not section or not term:
        return None

    rows = (
        db.query(SectionStaff)
        .filter_by(
            section_id=section_id,
            user_id=user_id,
            is_active=True,
        )
        .all()
    )
    roles = [row.staff_role for row in rows]

    if term.status == ARCHIVED_TERM_STATUS:
        roles = [
            role
            for role in roles
            if role in ARCHIVED_READ_STAFF_ROLES
        ]
    elif term.status in MUTABLE_TERM_STATUSES:
        if not section.is_active:
            roles = []
    else:
        roles = []

    if not roles:
        return None

    rank = {
        "reviewer": 1,
        "ta": 2,
        "instructor": 3,
        "course_owner": 4,
    }
    known = [role for role in roles if role in rank]
    return max(known, key=lambda role: rank[role]) if known else None


def accessible_staff_section_ids(
    db: Session,
    user_id: int,
) -> set[int]:
    return {
        assignment.section_id
        for assignment in valid_staff_assignments(db, user_id)
    }


def has_course_owner_assignment(
    db: Session,
    user_id: int | None,
) -> bool:
    if not user_id:
        return False
    return (
        db.query(SectionStaff)
        .filter_by(
            user_id=user_id,
            staff_role="course_owner",
            is_active=True,
        )
        .first()
        is not None
    )


def archive_active_term_reviews(
    db: Session,
    term_id: int,
    *,
    when: datetime | None = None,
) -> int:
    """Close active reviews without rewriting their engineering record.

    Semester archive is an administrative lifecycle boundary, not a successful
    review completion. Active ReviewSession rows are therefore preserved and
    transitioned to ``archived_incomplete``. Existing ReviewTurn rows, frozen
    EvidenceSnapshot rows, finding state, and committed reasoning remain
    untouched.

    ``completed_at`` is the existing persisted end timestamp on ReviewSession;
    for this terminal state it records when the session became non-mutable, not
    that the student completed the review normally. The challenge-state marker
    makes that distinction explicit for replay and future UI presentation.
    """
    section_ids = [
        row.id
        for row in (
            db.query(CourseSection)
            .filter_by(term_id=term_id)
            .all()
        )
    ]
    if not section_ids:
        return 0

    team_ids = [
        row.team_id
        for row in (
            db.query(TeamSection)
            .filter(TeamSection.section_id.in_(section_ids))
            .all()
        )
    ]
    if not team_ids:
        return 0

    archived_at = when or datetime.now(timezone.utc)
    sessions = (
        db.query(ReviewSession)
        .filter(
            ReviewSession.team_id.in_(team_ids),
            ReviewSession.status == "active",
        )
        .all()
    )

    for session in sessions:
        try:
            state = json.loads(session.challenge_state_json or "{}")
            if not isinstance(state, dict):
                state = {}
        except (TypeError, ValueError, json.JSONDecodeError):
            state = {}

        state["semester_lifecycle"] = {
            "status": "archived_incomplete",
            "reason": "term_archived",
            "archived_at": archived_at.isoformat(),
        }
        session.challenge_state_json = json.dumps(state)
        session.status = "archived_incomplete"
        session.completed_at = archived_at

    return len(sessions)


def revoke_term_sessions(
    db: Session,
    term_id: int,
    *,
    when: datetime | None = None,
) -> int:
    section_ids = [
        row.id
        for row in (
            db.query(CourseSection)
            .filter_by(term_id=term_id)
            .all()
        )
    ]
    if not section_ids:
        return 0

    user_ids = {
        row.user_id
        for row in (
            db.query(SectionEnrollment)
            .filter(SectionEnrollment.section_id.in_(section_ids))
            .all()
        )
    }
    user_ids.update(
        row.user_id
        for row in (
            db.query(SectionStaff)
            .filter(SectionStaff.section_id.in_(section_ids))
            .all()
        )
    )
    if not user_ids:
        return 0

    revoked_at = when or datetime.now(timezone.utc)
    return (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id.in_(user_ids),
            AuthSession.revoked_at.is_(None),
        )
        .update(
            {AuthSession.revoked_at: revoked_at},
            synchronize_session=False,
        )
    )


def set_term_status(
    db: Session,
    term: CourseTerm,
    status: str,
) -> CourseTerm:
    current_status = term.status

    # Semester lifecycle is forward-only in normal operation:
    # setup -> active -> archived. Repeating the current state is harmless,
    # but active terms cannot be moved backward into setup and archived terms
    # cannot be reopened.
    if current_status == status:
        return term

    if current_status == ARCHIVED_TERM_STATUS:
        raise HTTPException(
            status_code=409,
            detail="Archived terms cannot be reopened",
        )

    if current_status == ACTIVE_TERM_STATUS and status == "setup":
        raise HTTPException(
            status_code=409,
            detail="Active terms cannot return to setup",
        )

    if status == ARCHIVED_TERM_STATUS:
        archived_at = datetime.now(timezone.utc)
        term.status = ARCHIVED_TERM_STATUS
        archive_active_term_reviews(db, term.id, when=archived_at)
        revoke_term_sessions(db, term.id, when=archived_at)
        return term

    term.status = status
    return term
