"""
Multi-replica concurrency contracts for ETIS Engineering Studio.

Correctness must not depend on process-local locks. PostgreSQL constraints and
transactions must preserve review-turn ordering and request idempotency when
multiple application replicas serve the same review session.
"""

from sqlalchemy import UniqueConstraint

from apps.api.app.models import ReviewTurn


def _unique_column_sets(table):
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_review_turn_schema_enforces_sequence_and_client_idempotency():
    """
    Review turns require database-enforced ordering and idempotency.

    Reviewer turns do not have a client request identifier, so client_turn_id
    must remain nullable. Student/browser requests use the value to guarantee
    that the same logical turn cannot be persisted twice across app replicas.
    """
    table = ReviewTurn.__table__

    assert "client_turn_id" in table.c, (
        "ReviewTurn.client_turn_id must be a first-class database column; "
        "JSON metadata cannot enforce multi-replica idempotency"
    )

    client_turn_id = table.c.client_turn_id
    assert client_turn_id.nullable is True
    assert getattr(client_turn_id.type, "length", None) == 120

    unique_columns = _unique_column_sets(table)

    assert frozenset({"session_id", "sequence"}) in unique_columns, (
        "ReviewTurn must enforce one sequence number per review session"
    )

    assert frozenset({"session_id", "client_turn_id"}) in unique_columns, (
        "ReviewTurn must enforce one client turn ID per review session"
    )


def test_review_response_persists_client_turn_id_as_database_column(monkeypatch):
    """
    Browser idempotency keys must be persisted in the constrained database
    column, not only embedded inside signals_json.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.db import SessionLocal
    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]

    def fake_converse(*args, **kwargs):
        return (
            {
                "text": "Test reviewer follow-up.",
                "lens": "chief_architect",
                "provider": "deterministic",
                "kind": "coaching",
                "reviewer": {
                    "name": "Test Reviewer",
                    "role": "Reviewer",
                },
                "target_move": "consequence_visible",
                "guidance_refs": [],
                "teach_back": False,
            },
            {"consequence_visible": True},
            {
                "signals": {"consequence_visible": True},
                "ready_to_commit": False,
            },
        )

    monkeypatch.setattr(
        reviews_router.engine,
        "converse",
        fake_converse,
    )

    client_turn_id = "multi-replica-turn-001"

    response = client.post(
        f"/api/v1/reviews/{session_id}/respond",
        json={
            "response": "The engineering consequence is now explicit.",
            "evidence_refs": [],
            "decision": None,
            "intent": "discuss",
            "client_turn_id": client_turn_id,
        },
    )

    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        student_turn = (
            db.query(ReviewTurn)
            .filter_by(
                session_id=session_id,
                actor="student",
            )
            .order_by(ReviewTurn.sequence.desc())
            .first()
        )

        assert student_turn is not None
        assert student_turn.client_turn_id == client_turn_id, (
            "The browser idempotency key must be persisted in "
            "ReviewTurn.client_turn_id"
        )
    finally:
        db.close()


def test_review_session_lock_statement_uses_database_row_lock():
    """
    Review conversation serialization must use a database row lock.

    Process-local threading locks cannot coordinate separate Azure application
    replicas. The authoritative review-session mutation path therefore needs a
    SELECT ... FOR UPDATE statement that PostgreSQL can enforce across replicas.
    """
    from sqlalchemy.dialects import postgresql

    from apps.api.app.routers import reviews as reviews_router

    assert hasattr(reviews_router, "_review_session_for_update_stmt"), (
        "Review mutations need a database-backed review-session lock helper; "
        "process-local threading.Lock is insufficient across app replicas"
    )

    statement = reviews_router._review_session_for_update_stmt(123)

    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).upper()

    assert "FROM REVIEW_SESSIONS" in compiled
    assert "REVIEW_SESSIONS.ID = 123" in compiled
    assert "FOR UPDATE" in compiled, (
        "The review-session mutation statement must acquire a PostgreSQL "
        "row-level lock before calculating turn sequence or calling the reviewer"
    )


def test_review_response_acquires_database_lock_before_reviewer_call(monkeypatch):
    """
    The response mutation path must acquire the PostgreSQL review-session row
    lock before invoking semantic/reviewer processing.

    This prevents separate application replicas from simultaneously calculating
    the same next sequence, calling the reviewer twice, and overwriting review
    state.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]

    events = []

    original_lock_statement = reviews_router._review_session_for_update_stmt

    def observed_lock_statement(requested_session_id):
        events.append(("lock", requested_session_id))
        return original_lock_statement(requested_session_id)

    monkeypatch.setattr(
        reviews_router,
        "_review_session_for_update_stmt",
        observed_lock_statement,
    )

    def fake_converse(*args, **kwargs):
        events.append(("reviewer", session_id))
        return (
            {
                "text": "Serialized reviewer follow-up.",
                "lens": "chief_architect",
                "provider": "deterministic",
                "kind": "coaching",
                "reviewer": {
                    "name": "Test Reviewer",
                    "role": "Reviewer",
                },
                "target_move": "consequence_visible",
                "guidance_refs": [],
                "teach_back": False,
            },
            {"consequence_visible": True},
            {
                "signals": {"consequence_visible": True},
                "ready_to_commit": False,
            },
        )

    monkeypatch.setattr(
        reviews_router.engine,
        "converse",
        fake_converse,
    )

    response = client.post(
        f"/api/v1/reviews/{session_id}/respond",
        json={
            "response": "This turn must be serialized across replicas.",
            "evidence_refs": [],
            "decision": None,
            "intent": "discuss",
            "client_turn_id": "lock-order-turn-001",
        },
    )

    assert response.status_code == 200, response.text

    assert events, "Expected database lock and reviewer events"
    assert events[0] == ("lock", session_id), (
        "The review-session database row lock must be acquired before "
        "semantic/reviewer processing begins"
    )
    assert ("reviewer", session_id) in events


def test_clarify_and_coach_acquire_database_lock_before_reviewer_call(monkeypatch):
    """
    Every semantic review mutation path must acquire the database row lock
    before invoking reviewer processing.

    Protecting only /respond would still allow /clarify or /coach requests on
    another application replica to race the same ReviewSession state.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    original_lock_statement = (
        reviews_router._review_session_for_update_stmt
    )

    for route, body in (
        (
            "clarify",
            {
                "question": "What consequence should I be considering?",
                "client_turn_id": "clarify-lock-001",
            },
        ),
        (
            "coach",
            {
                "decision": None,
                "client_turn_id": "coach-lock-001",
            },
        ),
    ):
        started = client.post(
            "/api/v1/reviews/start",
            json={
                "team_id": seeded["team_id"],
                "user_id": seeded["user_id"],
                "phase_id": "A1",
                "mode": "board_review",
            },
        )
        assert started.status_code == 200, started.text
        session_id = started.json()["session_id"]

        events = []

        def observed_lock_statement(requested_session_id):
            events.append(("lock", requested_session_id))
            return original_lock_statement(requested_session_id)

        monkeypatch.setattr(
            reviews_router,
            "_review_session_for_update_stmt",
            observed_lock_statement,
        )

        def fake_converse(*args, **kwargs):
            events.append(("reviewer", session_id))
            return (
                {
                    "text": "Serialized reviewer follow-up.",
                    "lens": "chief_architect",
                    "provider": "deterministic",
                    "kind": "coaching",
                    "reviewer": {
                        "name": "Test Reviewer",
                        "role": "Reviewer",
                    },
                    "target_move": "consequence_visible",
                    "guidance_refs": [],
                    "teach_back": False,
                },
                {"consequence_visible": True},
                {
                    "signals": {"consequence_visible": True},
                    "ready_to_commit": False,
                },
            )

        monkeypatch.setattr(
            reviews_router.engine,
            "converse",
            fake_converse,
        )

        response = client.post(
            f"/api/v1/reviews/{session_id}/{route}",
            json=body,
        )

        assert response.status_code == 200, response.text
        assert events, f"Expected lock and reviewer events for /{route}"
        assert events[0] == ("lock", session_id), (
            f"/{route} must acquire the database review-session lock "
            "before reviewer processing"
        )
        assert ("reviewer", session_id) in events


def test_evidence_dispute_acquires_database_lock_before_mutating_review(monkeypatch):
    """
    Evidence disputes append ReviewTurn rows and mutate ReviewSession state.

    They must therefore acquire the same authoritative database row lock used
    by the semantic conversation paths before calculating the next sequence or
    changing review state.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text

    payload = started.json()
    session_id = payload["session_id"]

    finding = payload["evidence"]["findings"][0]
    evidence_ref = next(
        ref
        for ref in finding.get("evidence_refs", [])
        if str(ref).startswith("PATH:")
    )
    path = str(evidence_ref)[5:]

    events = []

    original_lock_statement = reviews_router._review_session_for_update_stmt

    def observed_lock_statement(requested_session_id):
        events.append(("lock", requested_session_id))
        return original_lock_statement(requested_session_id)

    monkeypatch.setattr(
        reviews_router,
        "_review_session_for_update_stmt",
        observed_lock_statement,
    )

    response = client.post(
        f"/api/v1/reviews/{session_id}/evidence-dispute",
        json={
            "path": path,
            "finding_id": finding["id"],
            "explanation": (
                "This exact frozen artifact should be reconsidered before "
                "the finding is treated as authoritative."
            ),
        },
    )

    assert response.status_code == 200, response.text

    assert events, (
        "Evidence-dispute mutation did not acquire the database review-session lock"
    )
    assert events[0] == ("lock", session_id)


def test_review_complete_acquires_database_lock_before_mutating_session(monkeypatch):
    """
    Completing a review changes authoritative ReviewSession state.

    Completion must participate in the same database row-lock protocol as
    conversation mutations so another application replica cannot append or
    overwrite review state while the session is being completed.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]

    events = []

    original_lock_statement = reviews_router._review_session_for_update_stmt

    def observed_lock_statement(requested_session_id):
        events.append(("lock", requested_session_id))
        return original_lock_statement(requested_session_id)

    monkeypatch.setattr(
        reviews_router,
        "_review_session_for_update_stmt",
        observed_lock_statement,
    )

    response = client.post(
        f"/api/v1/reviews/{session_id}/complete",
    )

    assert response.status_code == 200, response.text

    assert events, (
        "Review completion did not acquire the database review-session lock"
    )
    assert events[0] == ("lock", session_id)


def test_review_commit_acquires_database_lock_before_mutating_session(monkeypatch):
    """
    Stating a recommendation appends a ReviewTurn and changes ReviewSession
    state, so it must participate in the authoritative database row-lock
    protocol used by all other review-session mutations.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]

    # The commit route expects a current student position. Seed one directly
    # through the persisted review state so this test remains focused on the
    # concurrency contract rather than semantic readiness policy.
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import ReviewSession
    import json

    db = SessionLocal()
    try:
        session = db.get(ReviewSession, session_id)
        state = json.loads(session.challenge_state_json or "{}")
        state["last_student_position"] = {
            "response": "Proceed with the current recommendation.",
            "decision": "proceed",
            "evidence_refs": [],
        }
        state["evaluation"] = {
            "ready_to_commit": True,
        }
        session.challenge_state_json = json.dumps(state)
        db.commit()
    finally:
        db.close()

    events = []

    original_lock_statement = reviews_router._review_session_for_update_stmt

    def observed_lock_statement(requested_session_id):
        events.append(("lock", requested_session_id))
        return original_lock_statement(requested_session_id)

    monkeypatch.setattr(
        reviews_router,
        "_review_session_for_update_stmt",
        observed_lock_statement,
    )

    response = client.post(
        f"/api/v1/reviews/{session_id}/commit",
    )

    assert response.status_code == 200, response.text

    assert events, (
        "Recommendation commit did not acquire the database review-session lock"
    )
    assert events[0] == ("lock", session_id)


def test_review_session_lock_refreshes_already_loaded_orm_state():
    """
    The authoritative row-lock SELECT must refresh an existing ReviewSession
    instance in SQLAlchemy's identity map.

    Review routes currently perform an initial authorization lookup before
    acquiring the database lock. If another replica commits while this request
    waits for FOR UPDATE, the locking SELECT must replace those pre-wait ORM
    attribute values with the newly committed database state.
    """
    from apps.api.app.routers import reviews as reviews_router

    statement = reviews_router._review_session_for_update_stmt(123)
    options = statement.get_execution_options()

    assert options.get("populate_existing") is True, (
        "The review-session FOR UPDATE statement must use populate_existing "
        "so post-lock logic cannot continue from stale pre-wait ORM state"
    )


def test_identical_review_commit_retry_is_idempotent():
    """
    Retrying the same recommendation commit must not append another reviewer
    turn or rewrite the historical committed_at timestamp.
    """
    import json

    from fastapi.testclient import TestClient

    from apps.api.app.db import SessionLocal
    from apps.api.app.main import app
    from apps.api.app.models import ReviewSession, ReviewTurn

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]

    db = SessionLocal()
    try:
        session = db.get(ReviewSession, session_id)
        state = json.loads(session.challenge_state_json or "{}")
        state["last_student_position"] = {
            "response": "Proceed with the current recommendation.",
            "decision": "proceed",
            "evidence_refs": [],
        }
        state["evaluation"] = {
            "ready_to_commit": True,
        }
        session.challenge_state_json = json.dumps(state)
        db.commit()
    finally:
        db.close()

    first = client.post(
        f"/api/v1/reviews/{session_id}/commit",
    )
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload.get("duplicate") is False

    db = SessionLocal()
    try:
        turn_count_after_first = (
            db.query(ReviewTurn)
            .filter_by(session_id=session_id)
            .count()
        )
        session = db.get(ReviewSession, session_id)
        first_state = json.loads(session.challenge_state_json or "{}")
        first_committed_at = first_state["committed_position"]["committed_at"]
    finally:
        db.close()

    second = client.post(
        f"/api/v1/reviews/{session_id}/commit",
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()

    assert second_payload.get("duplicate") is True

    db = SessionLocal()
    try:
        turn_count_after_second = (
            db.query(ReviewTurn)
            .filter_by(session_id=session_id)
            .count()
        )
        session = db.get(ReviewSession, session_id)
        second_state = json.loads(session.challenge_state_json or "{}")
        second_committed_at = second_state["committed_position"]["committed_at"]

        assert turn_count_after_second == turn_count_after_first
        assert second_committed_at == first_committed_at
    finally:
        db.close()


def test_evidence_snapshot_lock_statement_uses_database_row_lock_and_refresh():
    """
    Finding state is shared across review sessions that use the same frozen
    evidence snapshot.

    ReviewSession locking alone cannot serialize two different sessions that
    update the same finding. Snapshot-scoped finding mutations therefore need
    a PostgreSQL SELECT ... FOR UPDATE lock on EvidenceSnapshot, with
    populate_existing so post-wait ORM state is fresh.
    """
    from sqlalchemy.dialects import postgresql

    from apps.api.app.routers import reviews as reviews_router

    assert hasattr(reviews_router, "_evidence_snapshot_for_update_stmt"), (
        "Finding-state mutations need a database-backed EvidenceSnapshot "
        "row-lock helper"
    )

    statement = reviews_router._evidence_snapshot_for_update_stmt(456)

    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).upper()

    assert "FROM EVIDENCE_SNAPSHOTS" in compiled
    assert "EVIDENCE_SNAPSHOTS.ID = 456" in compiled
    assert "FOR UPDATE" in compiled

    options = statement.get_execution_options()
    assert options.get("populate_existing") is True


def test_finding_disposition_acquires_snapshot_lock_before_state_update(monkeypatch):
    """
    Finding state belongs to the frozen EvidenceSnapshot, not to one review
    session.

    A disposition update must therefore acquire the authoritative snapshot row
    lock before calling the finding-state upsert path.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text

    payload = started.json()
    session_id = payload["session_id"]
    finding_id = payload["evidence"]["findings"][0]["id"]

    events = []

    original_snapshot_lock = (
        reviews_router._evidence_snapshot_for_update_stmt
    )

    def observed_snapshot_lock(snapshot_id):
        events.append(("snapshot_lock", snapshot_id))
        return original_snapshot_lock(snapshot_id)

    monkeypatch.setattr(
        reviews_router,
        "_evidence_snapshot_for_update_stmt",
        observed_snapshot_lock,
    )

    response = client.post(
        f"/api/v1/reviews/{session_id}/findings/{finding_id}/disposition",
        json={
            "status": "accepted_risk",
            "rationale": (
                "We understand the limitation and will revisit it "
                "before the next gate."
            ),
        },
    )

    assert response.status_code == 200, response.text

    assert events, (
        "Finding disposition did not acquire the EvidenceSnapshot database lock"
    )
    assert events[0][0] == "snapshot_lock"


def test_evidence_dispute_acquires_snapshot_lock_before_finding_state_update(
    monkeypatch,
):
    """
    Evidence disputes are session mutations, but a successful dispute may also
    change snapshot-scoped ReviewFindingState.

    When a dispute targets an existing frozen artifact and finding, it must
    acquire the EvidenceSnapshot row lock before updating shared finding state.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text

    payload = started.json()
    session_id = payload["session_id"]
    finding = payload["evidence"]["findings"][0]

    path_ref = next(
        ref
        for ref in finding.get("evidence_refs", [])
        if str(ref).startswith("PATH:")
    )
    path = str(path_ref)[5:]

    events = []

    original_snapshot_lock = (
        reviews_router._evidence_snapshot_for_update_stmt
    )

    def observed_snapshot_lock(snapshot_id):
        events.append(("snapshot_lock", snapshot_id))
        return original_snapshot_lock(snapshot_id)

    monkeypatch.setattr(
        reviews_router,
        "_evidence_snapshot_for_update_stmt",
        observed_snapshot_lock,
    )

    response = client.post(
        f"/api/v1/reviews/{session_id}/evidence-dispute",
        json={
            "path": path,
            "finding_id": finding["id"],
            "explanation": (
                "This frozen artifact materially changes how this exact "
                "finding should be interpreted."
            ),
        },
    )

    assert response.status_code == 200, response.text

    assert events, (
        "Evidence dispute updated finding state without acquiring the "
        "EvidenceSnapshot database lock"
    )
    assert events[0][0] == "snapshot_lock"


def test_team_lock_statement_uses_database_row_lock_and_refresh():
    """
    Review start snapshot establishment is team-scoped.

    Two application replicas starting reviews for the same team must serialize
    through the Team row before checking the frozen-snapshot cache or performing
    repository analysis. The locking SELECT must also refresh a Team instance
    already present in SQLAlchemy's identity map.
    """
    from sqlalchemy.dialects import postgresql

    from apps.api.app.routers import reviews as reviews_router

    assert hasattr(reviews_router, "_team_for_update_stmt"), (
        "Review start needs a database-backed Team row-lock helper so "
        "snapshot establishment cannot race across app replicas"
    )

    statement = reviews_router._team_for_update_stmt(789)

    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).upper()

    assert "FROM TEAMS" in compiled
    assert "TEAMS.ID = 789" in compiled
    assert "FOR UPDATE" in compiled

    options = statement.get_execution_options()
    assert options.get("populate_existing") is True


def test_review_start_acquires_team_lock_before_evidence_preparation(monkeypatch):
    """
    Review start must serialize on the Team row before evidence preparation.

    Locking only immediately before snapshot insertion would still allow two
    application replicas to perform the same repository/semantic analysis at
    the same time. The Team lock therefore has to precede orchestrator.prepare.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app
    from apps.api.app.routers import reviews as reviews_router

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    events = []

    original_team_lock = reviews_router._team_for_update_stmt
    original_prepare = reviews_router.orchestrator.prepare

    def observed_team_lock(team_id):
        events.append(("team_lock", team_id))
        return original_team_lock(team_id)

    def observed_prepare(*args, **kwargs):
        events.append(("prepare", seeded["team_id"]))
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(
        reviews_router,
        "_team_for_update_stmt",
        observed_team_lock,
    )
    monkeypatch.setattr(
        reviews_router.orchestrator,
        "prepare",
        observed_prepare,
    )

    response = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )

    assert response.status_code == 200, response.text

    assert events, "Expected Team lock and evidence-preparation events"
    assert events[0] == ("team_lock", seeded["team_id"]), (
        "Review start must acquire the database Team row lock before "
        "repository/evidence preparation begins"
    )
    assert ("prepare", seeded["team_id"]) in events


def test_postgresql_team_row_lock_blocks_independent_replica_until_commit():
    """
    Prove the production PostgreSQL locking behavior with independent
    connections.

    Replica A holds SELECT ... FOR UPDATE on a Team row. Replica B must enter
    PostgreSQL's Lock wait state and must not acquire that row until Replica A
    commits. This is the production-dialect proof that SQLite cannot provide.
    """
    import os
    import threading
    import time
    from pathlib import Path
    from uuid import uuid4

    import pytest
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from apps.api.app.models import Team
    from apps.api.app.routers import reviews as reviews_router

    database_url = os.getenv("ETIS_TEST_POSTGRES_URL", "").strip()

    if not database_url:
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            pytest.fail(
                "CI must provide ETIS_TEST_POSTGRES_URL so multi-replica "
                "locking is validated against PostgreSQL"
            )

        pytest.skip("ETIS_TEST_POSTGRES_URL is not configured")

    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)

    # This test may run before or after the migration contract test. Ensure
    # the dedicated CI PostgreSQL database is at the current schema head.
    command.upgrade(config, "head")

    pg_engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )
    PgSession = sessionmaker(
        bind=pg_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    suffix = uuid4().hex[:12]

    seed = PgSession()
    try:
        team = Team(
            course_namespace=f"LOCK-{suffix}",
            team_key="TEAM-01",
            name="PostgreSQL Lock Contract",
        )
        seed.add(team)
        seed.commit()
        team_id = team.id
    finally:
        seed.close()

    holder = PgSession()
    contender_thread = None
    contender_errors = []
    contender_pid = {}
    pid_ready = threading.Event()
    acquired = threading.Event()

    def contender():
        db = PgSession()
        try:
            contender_pid["value"] = db.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()
            pid_ready.set()

            db.execute(
                reviews_router._team_for_update_stmt(team_id)
            ).scalar_one()

            acquired.set()
            db.commit()
        except BaseException as exc:
            contender_errors.append(exc)
            pid_ready.set()
            db.rollback()
        finally:
            db.close()

    try:
        # Replica A acquires and holds the Team row lock.
        holder.execute(
            reviews_router._team_for_update_stmt(team_id)
        ).scalar_one()

        # Replica B uses a completely separate PostgreSQL connection.
        contender_thread = threading.Thread(
            target=contender,
            daemon=True,
        )
        contender_thread.start()

        assert pid_ready.wait(5), (
            "The contender PostgreSQL connection did not start"
        )
        assert not contender_errors
        assert "value" in contender_pid

        # Observe PostgreSQL itself reporting that Replica B is waiting on a
        # lock. This avoids relying only on timing assumptions.
        saw_lock_wait = False
        deadline = time.monotonic() + 5

        with pg_engine.connect() as observer:
            while time.monotonic() < deadline:
                row = observer.execute(
                    text(
                        """
                        SELECT wait_event_type, wait_event
                        FROM pg_stat_activity
                        WHERE pid = :pid
                        """
                    ),
                    {"pid": contender_pid["value"]},
                ).mappings().first()

                if (
                    row
                    and row.get("wait_event_type") == "Lock"
                ):
                    saw_lock_wait = True
                    break

                if acquired.is_set():
                    break

                time.sleep(0.05)

        assert saw_lock_wait, (
            "PostgreSQL did not report the independent replica waiting "
            "on the Team row lock"
        )
        assert not acquired.is_set(), (
            "The competing replica acquired the Team row before the "
            "holding transaction committed"
        )

        # Replica A commits. Replica B must now resume and acquire the row.
        holder.commit()

        assert acquired.wait(5), (
            "The competing replica did not acquire the Team row after "
            "the holding transaction committed"
        )

        contender_thread.join(timeout=5)
        assert not contender_thread.is_alive()
        assert contender_errors == []

    finally:
        # Always release the holder lock even if an assertion fails.
        if holder.in_transaction():
            holder.rollback()
        holder.close()

        if contender_thread is not None and contender_thread.is_alive():
            contender_thread.join(timeout=5)

        cleanup = PgSession()
        try:
            persisted_team = cleanup.get(Team, team_id)
            if persisted_team is not None:
                cleanup.delete(persisted_team)
                cleanup.commit()
        finally:
            cleanup.close()

        pg_engine.dispose()


def test_identical_evidence_dispute_retry_is_idempotent():
    """
    Retrying the same logical evidence dispute must not append duplicate turns
    or duplicate review-state history.

    Browser/network retries identify the logical request with client_turn_id.
    The second request must return the already-recorded dispute result.
    """
    import json

    from fastapi.testclient import TestClient

    from apps.api.app.db import SessionLocal
    from apps.api.app.main import app
    from apps.api.app.models import ReviewSession, ReviewTurn

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text

    payload = started.json()
    session_id = payload["session_id"]
    finding = payload["evidence"]["findings"][0]

    path_ref = next(
        ref
        for ref in finding.get("evidence_refs", [])
        if str(ref).startswith("PATH:")
    )
    path = str(path_ref)[5:]

    request_body = {
        "path": path,
        "finding_id": finding["id"],
        "explanation": (
            "This exact frozen artifact changes how this finding "
            "should be interpreted."
        ),
        "client_turn_id": "evidence-dispute-retry-001",
    }

    first = client.post(
        f"/api/v1/reviews/{session_id}/evidence-dispute",
        json=request_body,
    )
    assert first.status_code == 200, first.text

    db = SessionLocal()
    try:
        turn_count_after_first = (
            db.query(ReviewTurn)
            .filter_by(session_id=session_id)
            .count()
        )

        session = db.get(ReviewSession, session_id)
        first_state = json.loads(session.challenge_state_json or "{}")
        dispute_count_after_first = len(
            first_state.get("evidence_disputes") or []
        )
    finally:
        db.close()

    second = client.post(
        f"/api/v1/reviews/{session_id}/evidence-dispute",
        json=request_body,
    )
    assert second.status_code == 200, second.text

    second_payload = second.json()
    assert second_payload.get("duplicate") is True, (
        "The repeated client_turn_id must return the previously recorded "
        "evidence-dispute result"
    )

    db = SessionLocal()
    try:
        turn_count_after_second = (
            db.query(ReviewTurn)
            .filter_by(session_id=session_id)
            .count()
        )

        session = db.get(ReviewSession, session_id)
        second_state = json.loads(session.challenge_state_json or "{}")
        dispute_count_after_second = len(
            second_state.get("evidence_disputes") or []
        )

        assert turn_count_after_second == turn_count_after_first
        assert dispute_count_after_second == dispute_count_after_first
    finally:
        db.close()


def test_client_turn_id_cannot_be_reused_across_review_operations():
    """
    A session-scoped client_turn_id belongs to one logical operation.

    If an evidence dispute already owns an idempotency key, a later
    conversation request must not interpret that dispute as its own duplicate
    result. Cross-operation key reuse must fail closed with HTTP 409.
    """
    from fastapi.testclient import TestClient

    from apps.api.app.main import app

    client = TestClient(app)

    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seeded = seed.json()

    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seeded["team_id"],
            "user_id": seeded["user_id"],
            "phase_id": "A1",
            "mode": "board_review",
        },
    )
    assert started.status_code == 200, started.text

    payload = started.json()
    session_id = payload["session_id"]
    finding = payload["evidence"]["findings"][0]

    path_ref = next(
        ref
        for ref in finding.get("evidence_refs", [])
        if str(ref).startswith("PATH:")
    )
    path = str(path_ref)[5:]

    shared_id = "cross-operation-id-001"

    dispute = client.post(
        f"/api/v1/reviews/{session_id}/evidence-dispute",
        json={
            "path": path,
            "finding_id": finding["id"],
            "explanation": (
                "This frozen artifact changes how the finding should "
                "be interpreted."
            ),
            "client_turn_id": shared_id,
        },
    )
    assert dispute.status_code == 200, dispute.text

    response = client.post(
        f"/api/v1/reviews/{session_id}/respond",
        json={
            "response": (
                "This is a different logical operation and must not "
                "inherit the dispute result."
            ),
            "evidence_refs": [],
            "decision": None,
            "intent": "discuss",
            "client_turn_id": shared_id,
        },
    )

    assert response.status_code == 409, (
        "A client_turn_id already owned by an evidence dispute must not "
        "be interpreted as a duplicate conversation turn"
    )
