from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from apps.api.app.db import SessionLocal
from apps.api.app.models import (
    CourseSection,
    CourseTerm,
    InstitutionalIdentity,
    SectionEnrollment,
    User,
)
from apps.api.app.routers import auth as auth_router
from apps.api.app.services import auth as auth_service


LOYOLA_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_TENANT_ID = "22222222-2222-2222-2222-222222222222"
TEST_OID = "33333333-3333-3333-3333-333333333333"


def _settings(**overrides):
    values = {
        "entra_authority": "organizations",
        "entra_allowed_tenant_id": LOYOLA_TENANT_ID,
        "entra_allowed_domain": "luc.edu",
        "entra_client_id": "entra-client",
        "entra_client_secret": "entra-secret",
        "entra_redirect_uri": "https://studio.example.edu/auth/entra/callback",
        "etis_production_test_student_tenant_id": TEST_TENANT_ID,
        "etis_production_test_student_oid": TEST_OID,
        "etis_production_test_student_email": "test-student@example.net",
        "etis_production_test_student_id": "production-test-student",
        "etis_bootstrap_owner_email": "",
        "etis_env": "production",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _request(cookie_value: str | None = None) -> Request:
    headers = []
    if cookie_value is not None:
        headers.append(
            (
                b"cookie",
                f"etis_entra_flow={cookie_value}".encode("ascii"),
            )
        )
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/entra/callback",
            "headers": headers,
        }
    )


def test_entra_authorization_uses_organizations_not_trusted_tenant(monkeypatch):
    monkeypatch.setattr(auth_service, "get_settings", _settings)

    url = auth_service.entra_authorize_url("signed-state", "nonce-value")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path == "/organizations/oauth2/v2.0/authorize"
    assert LOYOLA_TENANT_ID not in parsed.path
    assert query["state"] == ["signed-state"]
    assert query["nonce"] == ["nonce-value"]


def test_entra_login_sets_short_lived_browser_binding_cookie(monkeypatch):
    captured = {}
    monkeypatch.setattr(auth_router, "get_settings", _settings)
    monkeypatch.setattr(
        auth_router.secrets,
        "token_urlsafe",
        lambda size: "browser-flow-binding",
    )
    monkeypatch.setattr(
        auth_router,
        "create_flow_state",
        lambda kind, payload: captured.update(
            {"kind": kind, "payload": payload}
        ) or "signed-state",
    )
    monkeypatch.setattr(
        auth_router,
        "parse_flow_state",
        lambda state, kind: {"nonce": "nonce-value"},
    )
    monkeypatch.setattr(
        auth_router,
        "entra_authorize_url",
        lambda state, nonce: "https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize",
    )

    response = auth_router.entra_login()

    assert captured == {
        "kind": "entra",
        "payload": {"flow_binding": "browser-flow-binding"},
    }
    cookie = response.headers["set-cookie"].lower()
    assert "etis_entra_flow=browser-flow-binding" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=600" in cookie
    assert "path=/auth/entra" in cookie


@pytest.mark.parametrize("cookie_value", [None, "different-browser"])
def test_entra_callback_rejects_unbound_browser_before_code_exchange(
    monkeypatch,
    cookie_value,
):
    monkeypatch.setattr(
        auth_router,
        "parse_flow_state",
        lambda state, kind: {
            "nonce": "expected-nonce",
            "flow_binding": "initiating-browser",
        },
    )

    exchanges = []
    monkeypatch.setattr(
        auth_router,
        "entra_exchange",
        lambda *args, **kwargs: exchanges.append(True),
    )

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc:
            auth_router.entra_callback(
                code="authorization-code",
                state="signed-state",
                request=_request(cookie_value),
                db=db,
            )
    finally:
        db.close()

    assert exc.value.status_code == 400
    assert exchanges == []


def test_luc_email_from_untrusted_tenant_is_rejected(monkeypatch):
    monkeypatch.setattr(auth_service, "get_settings", _settings)

    with pytest.raises(HTTPException) as exc:
        auth_service.resolve_entra_identity(
            {
                "tid": "99999999-9999-9999-9999-999999999999",
                "oid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "preferred_username": "student@luc.edu",
            }
        )

    assert exc.value.status_code == 403
    assert "tenant" in str(exc.value.detail).lower()


def test_test_object_id_without_exact_test_tenant_is_rejected(monkeypatch):
    monkeypatch.setattr(auth_service, "get_settings", _settings)

    with pytest.raises(HTTPException) as exc:
        auth_service.resolve_entra_identity(
            {
                "tid": "99999999-9999-9999-9999-999999999999",
                "oid": TEST_OID,
                "preferred_username": "test-student@example.net",
            }
        )

    assert exc.value.status_code == 403


def test_database_rejects_duplicate_tenant_scoped_principal():
    db = SessionLocal()
    try:
        first = User(
            github_login="luc:first-tenant-principal",
            display_name="First",
            role="student",
        )
        second = User(
            github_login="luc:second-tenant-principal",
            display_name="Second",
            role="student",
        )
        db.add_all((first, second))
        db.flush()
        db.add_all(
            (
                InstitutionalIdentity(
                    user_id=first.id,
                    student_id="first-tenant-principal",
                    institutional_email="first-tenant-principal@luc.edu",
                    provider_tenant_id=LOYOLA_TENANT_ID,
                    provider_subject="shared-object-id",
                ),
                InstitutionalIdentity(
                    user_id=second.id,
                    student_id="second-tenant-principal",
                    institutional_email="second-tenant-principal@luc.edu",
                    provider_tenant_id=LOYOLA_TENANT_ID,
                    provider_subject="shared-object-id",
                ),
            )
        )

        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_successful_loyola_callback_binds_tenant_and_object_id(monkeypatch):
    db = SessionLocal()
    try:
        user = User(
            github_login="luc:sam",
            display_name="Sam Student",
            role="student",
        )
        db.add(user)
        db.flush()

        term = CourseTerm(
            namespace="COMP330-ENTRA-MULTITENANT-TEST",
            term_label="Entra Multitenant Test",
            status="active",
        )
        db.add(term)
        db.flush()
        section = CourseSection(
            term_id=term.id,
            section_key="001",
            display_name="Section 001",
            is_active=True,
        )
        db.add(section)
        db.flush()
        identity = InstitutionalIdentity(
            user_id=user.id,
            student_id="sam",
            institutional_email="sam@luc.edu",
        )
        db.add(identity)
        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=user.id,
                status="active",
            )
        )
        db.commit()

        settings = _settings(etis_env="development")
        monkeypatch.setattr(auth_router, "get_settings", lambda: settings)
        monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
        monkeypatch.setattr(
            auth_router,
            "parse_flow_state",
            lambda state, kind: {
                "nonce": "expected-nonce",
                "flow_binding": "initiating-browser",
            },
        )
        monkeypatch.setattr(
            auth_router,
            "entra_exchange",
            lambda code, nonce: {
                "tid": LOYOLA_TENANT_ID,
                "oid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "preferred_username": "sam@luc.edu",
                "name": "Sam Student",
            },
        )

        response = auth_router.entra_callback(
            code="authorization-code",
            state="signed-state",
            request=_request("initiating-browser"),
            db=db,
        )

        db.refresh(identity)
        assert response.status_code == 307
        assert identity.provider_tenant_id == LOYOLA_TENANT_ID
        assert identity.provider_subject == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        cookies = "\n".join(response.headers.getlist("set-cookie")).lower()
        assert "etis_session=" in cookies
        assert "etis_entra_flow=" in cookies
        assert "max-age=0" in cookies

    finally:
        db.close()
