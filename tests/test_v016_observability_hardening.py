import json
import logging
import re
import pytest

from fastapi.testclient import TestClient

from apps.api.app.main import app



@pytest.fixture
def observability_records():
    """
    Capture ETIS observability records with a test-owned handler.

    Production intentionally disables propagation, so tests attach directly
    to the dedicated logger without depending on pytest's global caplog
    lifecycle.
    """
    logger = logging.getLogger("etis.observability")

    class Capture:
        def __init__(self):
            self.records = []

    capture = Capture()

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            capture.records.append(record)

    handler = CaptureHandler(level=logging.INFO)
    logger.addHandler(handler)

    try:
        yield capture
    finally:
        logger.removeHandler(handler)


UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-"
    r"[0-9a-f]{4}-"
    r"4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-"
    r"[0-9a-f]{12}$"
)


def test_http_observability_emits_safe_request_metadata_only(observability_records):
    secret_email = "student.private@luc.edu"
    secret_bearer = "Bearer ETIS-GATE11-SUPER-SECRET-TOKEN"
    secret_cookie = "ETIS-GATE11-SESSION-COOKIE"

    with TestClient(app) as client:
        response = client.get(
            f"/health?email={secret_email}&token=do-not-log-this",
            headers={
                "Authorization": secret_bearer,
                "Cookie": f"etis_session={secret_cookie}",
            },
        )

    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert UUID_PATTERN.fullmatch(request_id)

    records = [
        record
        for record in observability_records.records
        if record.name == "etis.observability"
        and getattr(record, "event", None) == "http_request"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.method == "GET"
    assert record.route == "/health"
    assert record.status_code == 200
    assert isinstance(record.duration_ms, (int, float))
    assert record.duration_ms >= 0
    assert record.request_id == request_id

    structured = json.loads(record.getMessage())

    assert structured == {
        "event": "http_request",
        "request_id": request_id,
        "method": "GET",
        "route": "/health",
        "status_code": 200,
        "duration_ms": record.duration_ms,
    }

    rendered = " ".join(
        [
            record.getMessage(),
            repr(record.__dict__),
        ]
    )

    for forbidden in (
        secret_email,
        secret_bearer,
        secret_cookie,
        "do-not-log-this",
    ):
        assert forbidden not in rendered


def test_unhandled_failure_observability_is_correlated_and_does_not_log_exception_message(
    observability_records,
    monkeypatch,
):
    from apps.api.app import main as main_module

    secret = "ETIS-GATE11-DO-NOT-LOG-THIS-SECRET"

    def fail_database_readiness():
        raise RuntimeError(secret)

    monkeypatch.setattr(
        main_module,
        "database_readiness",
        fail_database_readiness,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/ready")

    assert response.status_code == 500

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert UUID_PATTERN.fullmatch(request_id)

    records = [
        record
        for record in observability_records.records
        if record.name == "etis.observability"
        and getattr(record, "event", None) == "http_request"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.method == "GET"
    assert record.route == "/ready"
    assert record.status_code == 500
    assert record.request_id == request_id
    assert record.error_type == "RuntimeError"
    assert record.levelno == logging.ERROR
    assert isinstance(record.duration_ms, (int, float))
    assert record.duration_ms >= 0

    rendered = " ".join(
        [
            record.getMessage(),
            repr(record.__dict__),
        ]
    )

    assert secret not in rendered
    assert secret not in response.text


def test_csrf_rejection_is_correlated_without_logging_session_content(observability_records):
    secret_cookie = "ETIS-GATE11-CSRF-SESSION-SECRET"

    with TestClient(app) as client:
        response = client.post(
            "/gate11-csrf-probe",
            headers={
                "Cookie": f"etis_session={secret_cookie}",
            },
        )

    assert response.status_code == 403

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert UUID_PATTERN.fullmatch(request_id)

    records = [
        record
        for record in observability_records.records
        if record.name == "etis.observability"
        and getattr(record, "event", None) == "http_request"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.method == "POST"
    assert record.status_code == 403
    assert record.request_id == request_id
    assert record.route == "<unmatched>"

    rendered = " ".join(
        [
            record.getMessage(),
            repr(record.__dict__),
        ]
    )

    assert secret_cookie not in rendered


def test_pre_routing_failure_never_logs_raw_unmatched_path(observability_records, monkeypatch):
    from apps.api.app import main as main_module

    sensitive_path_value = "ETIS-GATE11-SENSITIVE-PATH-987654"

    def fail_csrf_validation(*_args, **_kwargs):
        raise RuntimeError("bounded-test-failure")

    monkeypatch.setattr(
        main_module,
        "validate_csrf_token",
        fail_csrf_validation,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/does-not-exist/{sensitive_path_value}",
            headers={
                "Cookie": "etis_session=test-session",
                "X-CSRF-Token": "test-csrf",
            },
        )

    assert response.status_code == 500

    records = [
        record
        for record in observability_records.records
        if record.name == "etis.observability"
        and getattr(record, "event", None) == "http_request"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.route == "<unmatched>"
    assert record.status_code == 500

    rendered = " ".join(
        [
            record.getMessage(),
            repr(record.__dict__),
        ]
    )

    assert sensitive_path_value not in rendered


def test_production_container_disables_uvicorn_raw_access_log():
    from pathlib import Path

    dockerfile = Path("apps/api/Dockerfile").read_text()

    assert '"--no-access-log"' in dockerfile, (
        "production Uvicorn access logging must be disabled; "
        "safe request telemetry is emitted by ETIS middleware"
    )


def test_observability_logger_has_dedicated_info_stream_sink():
    from apps.api.app import main as main_module

    logger = main_module.observability_logger

    assert logger.level == logging.INFO, (
        "ETIS observability logger must emit INFO request telemetry in production"
    )

    stream_handlers = [
        handler
        for handler in logger.handlers
        if isinstance(handler, logging.StreamHandler)
    ]

    assert stream_handlers, (
        "ETIS observability logger must have a dedicated stream sink "
        "for container log collection"
    )

    assert any(
        handler.formatter
        and handler.formatter._fmt == "%(message)s"
        for handler in stream_handlers
    ), (
        "observability stream sink must preserve the structured JSON message "
        "without adding request-sensitive formatter fields"
    )


def test_request_id_is_server_generated_not_caller_controlled(observability_records):
    attacker_supplied_id = "ETIS-GATE11-INJECTED-REQUEST-ID-SECRET"

    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": attacker_supplied_id,
            },
        )

    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert request_id != attacker_supplied_id
    assert UUID_PATTERN.fullmatch(request_id)

    records = [
        record
        for record in observability_records.records
        if record.name == "etis.observability"
        and getattr(record, "event", None) == "http_request"
    ]

    assert len(records) == 1
    assert records[0].request_id == request_id

    rendered = " ".join(
        [
            records[0].getMessage(),
            repr(records[0].__dict__),
        ]
    )

    assert attacker_supplied_id not in rendered


def test_request_body_content_is_never_logged(observability_records):
    secret_body_value = "ETIS-GATE11-PRIVATE-BODY-CONTENT"

    with TestClient(app) as client:
        response = client.post(
            "/gate11-body-probe",
            json={
                "message": secret_body_value,
                "password": "do-not-log-password",
            },
        )

    assert response.status_code == 404

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert UUID_PATTERN.fullmatch(request_id)

    records = [
        record
        for record in observability_records.records
        if record.name == "etis.observability"
        and getattr(record, "event", None) == "http_request"
    ]

    assert len(records) == 1

    record = records[0]

    assert record.method == "POST"
    assert record.route == "<unmatched>"
    assert record.status_code == 404
    assert record.request_id == request_id

    rendered = " ".join(
        [
            record.getMessage(),
            repr(record.__dict__),
        ]
    )

    assert secret_body_value not in rendered
    assert "do-not-log-password" not in rendered
