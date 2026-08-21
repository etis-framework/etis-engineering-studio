from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    github_login: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(30), default="student")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    """
    Server-side authentication session.

    The raw browser/bearer credential is never persisted. Only its SHA-256
    digest is stored, allowing immediate logout/revocation across app replicas.
    """
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )
    login: Mapped[str] = mapped_column(String(240), default="")
    requires_course_authorization: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_namespace: Mapped[str] = mapped_column(String(50), index=True)
    team_key: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(200))
    repo_full_name: Mapped[str] = mapped_column(String(250), default="")
    project_name: Mapped[str] = mapped_column(String(200), default="CampusConnect")
    current_phase: Mapped[str] = mapped_column(String(10), default="A1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("course_namespace", "team_key"),)


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    responsibility_role: Mapped[str] = mapped_column(String(100), default="Engineering Contributor")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    team = relationship("Team")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("team_id", "user_id"),)


class EvidenceSnapshot(Base):
    __tablename__ = "evidence_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    phase_id: Mapped[str] = mapped_column(String(10), index=True)
    source: Mapped[str] = mapped_column(String(30), default="demo")
    commit_sha: Mapped[str] = mapped_column(String(80), default="")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewSession(Base):
    __tablename__ = "review_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    client_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    phase_id: Mapped[str] = mapped_column(String(10), index=True)
    mode: Mapped[str] = mapped_column(String(30), default="guided_review")
    status: Mapped[str] = mapped_column(String(30), default="active")
    scenario_id: Mapped[str] = mapped_column(String(120), default="")
    challenge_state_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "client_request_id",
            name="uq_review_sessions_team_client_request_id",
        ),
    )


class ReviewTurn(Base):
    __tablename__ = "review_turns"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("review_sessions.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    client_turn_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor: Mapped[str] = mapped_column(String(50))
    lens: Mapped[str] = mapped_column(String(80), default="")
    content: Mapped[str] = mapped_column(Text)
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    signals_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "sequence",
            name="uq_review_turns_session_sequence",
        ),
        UniqueConstraint(
            "session_id",
            "client_turn_id",
            name="uq_review_turns_session_client_turn_id",
        ),
    )


class InstructorNote(Base):
    __tablename__ = "instructor_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    phase_id: Mapped[str] = mapped_column(String(10), default="")
    provenance: Mapped[str] = mapped_column(String(30), default="INSTRUCTOR")
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIUsageEvent(Base):
    __tablename__ = "ai_usage_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_namespace: Mapped[str] = mapped_column(String(50), index=True, default="")
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("review_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_id: Mapped[str] = mapped_column(String(10), default="", index=True)
    purpose: Mapped[str] = mapped_column(String(80), default="conversation", index=True)
    model: Mapped[str] = mapped_column(String(80), default="")
    response_id: Mapped[str] = mapped_column(String(120), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_microusd: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CourseTerm(Base):
    __tablename__ = "course_terms"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(40), default="COMP 330", index=True)
    namespace: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    term_label: Mapped[str] = mapped_column(String(100))
    starts_on: Mapped[str] = mapped_column(String(20), default="")
    ends_on: Mapped[str] = mapped_column(String(20), default="")
    timezone: Mapped[str] = mapped_column(String(80), default="America/Chicago")
    status: Mapped[str] = mapped_column(String(30), default="setup")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CourseSection(Base):
    __tablename__ = "course_sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("course_terms.id", ondelete="CASCADE"), index=True)
    section_key: Mapped[str] = mapped_column(String(40), index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    meeting_pattern: Mapped[str] = mapped_column(String(160), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("term_id", "section_key"),)


class InstitutionalIdentity(Base):
    __tablename__ = "institutional_identities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    student_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    institutional_email: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    identity_provider: Mapped[str] = mapped_column(String(40), default="loyola_entra")
    provider_subject: Mapped[str] = mapped_column(String(240), default="", index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user = relationship("User")


class SectionEnrollment(Base):
    __tablename__ = "section_enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("section_id", "user_id"),)


class SectionStaff(Base):
    __tablename__ = "section_staff"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    staff_role: Mapped[str] = mapped_column(String(40), default="instructor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("section_id", "user_id", "staff_role"),)


class TeamSection(Base):
    __tablename__ = "team_sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id", ondelete="CASCADE"), index=True)


class MembershipEvent(Base):
    __tablename__ = "membership_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    from_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    to_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(40), default="assigned")
    performed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PhaseSchedule(Base):
    __tablename__ = "phase_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id", ondelete="CASCADE"), index=True)
    phase_id: Mapped[str] = mapped_column(String(10), index=True)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accept_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_override: Mapped[str] = mapped_column(String(20), default="auto")
    instructor_note: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("section_id", "phase_id"),)


class GitHubIdentity(Base):
    __tablename__ = "github_identities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    github_login: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    github_user_id: Mapped[str] = mapped_column(String(80), default="")
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        Index(
            "uq_github_identities_github_user_id_nonempty",
            "github_user_id",
            unique=True,
            sqlite_where=text("github_user_id <> ''"),
            postgresql_where=text("github_user_id <> ''"),
        ),
    )


REPOSITORY_STATUS_CANDIDATE = "candidate"
REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED = "owner_authorization_required"
REPOSITORY_STATUS_VERIFIED = "verified"

REPOSITORY_OWNER_USER = "User"
REPOSITORY_OWNER_ORGANIZATION = "Organization"


class RepositoryConnection(Base):
    """
    Team repository onboarding state.

    ``repo_full_name`` is the current nominated candidate until ``status`` is
    ``verified``. ``Team.repo_full_name`` remains the authoritative evidence
    source and must not be populated from an unverified candidate.
    """

    __tablename__ = "repository_connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True)
    repo_full_name: Mapped[str] = mapped_column(String(260), index=True)
    clone_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default=REPOSITORY_STATUS_CANDIDATE)
    owner_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    owner_login: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner_github_account_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    github_app_installed: Mapped[bool] = mapped_column(Boolean, default=False)
    installation_id: Mapped[str] = mapped_column(String(100), default="")
    connected_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    authorization_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewFindingState(Base):
    __tablename__ = "review_finding_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("evidence_snapshots.id", ondelete="CASCADE"), index=True)
    finding_id: Mapped[str] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    evidence_path: Mapped[str] = mapped_column(String(500), default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (UniqueConstraint("snapshot_id", "finding_id"),)
