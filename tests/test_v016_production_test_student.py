from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from apps.api.app.config import Settings
from apps.api.app.services import auth as auth_service


ROOT = Path(__file__).resolve().parents[1]
AUTH_ROUTER = ROOT / "apps" / "api" / "app" / "routers" / "auth.py"
ADMIN_ROUTER = ROOT / "apps" / "api" / "app" / "routers" / "admin.py"
APP_BICEP = ROOT / "infra" / "azure" / "app.bicep"
DEPLOY = ROOT / ".github" / "workflows" / "deploy-azure.yml"


TEST_OID = "11111111-2222-3333-4444-555555555555"
TEST_EMAIL = "production-student@example.net"
TEST_STUDENT_ID = "production-test-student"
TEST_SECTION_KEY = "PRODUCTION-TEST"
TEST_TEAM_KEY = "production-test-team"


def test_settings_define_exact_production_test_student_contract():
    required = {
        "etis_production_test_student_oid",
        "etis_production_test_student_email",
        "etis_production_test_student_id",
        "etis_production_test_section_key",
        "etis_production_test_team_key",
    }

    assert required <= set(Settings.model_fields)


def test_entra_identity_resolution_allows_loyola_and_only_exact_test_oid(
    monkeypatch,
):
    assert hasattr(auth_service, "resolve_entra_identity"), (
        "Entra authorization needs one bounded identity-resolution function"
    )

    settings = SimpleNamespace(
        entra_allowed_domain="luc.edu",
        etis_production_test_student_oid=TEST_OID,
        etis_production_test_student_email=TEST_EMAIL,
    )
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)

    resolve = auth_service.resolve_entra_identity

    loyola = resolve(
        {
            "oid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "preferred_username": "student1@luc.edu",
        }
    )
    assert loyola == {
        "oid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "email": "student1@luc.edu",
        "is_production_test_student": False,
    }

    # A B2B guest may expose an Entra-formatted preferred_username rather than
    # the original Gmail address. Authorization is therefore based on the
    # configured tenant-scoped oid. The configured email is the canonical
    # Studio identity for that exact test principal.
    guest = resolve(
        {
            "oid": TEST_OID,
            "preferred_username": (
                "production-student_example.net"
                "#EXT#@exampletenant.onmicrosoft.com"
            ),
        }
    )
    assert guest == {
        "oid": TEST_OID,
        "email": TEST_EMAIL,
        "is_production_test_student": True,
    }

    # Merely presenting the configured email must never authorize another oid.
    with pytest.raises(HTTPException) as exc:
        resolve(
            {
                "oid": "99999999-8888-7777-6666-555555555555",
                "email": TEST_EMAIL,
            }
        )
    assert exc.value.status_code == 403


def test_entra_identity_resolution_requires_verified_oid(monkeypatch):
    assert hasattr(auth_service, "resolve_entra_identity")

    settings = SimpleNamespace(
        entra_allowed_domain="luc.edu",
        etis_production_test_student_oid=TEST_OID,
        etis_production_test_student_email=TEST_EMAIL,
    )
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)

    with pytest.raises(HTTPException) as exc:
        auth_service.resolve_entra_identity(
            {"preferred_username": "student1@luc.edu"}
        )

    assert exc.value.status_code in {401, 403}


def test_entra_callback_uses_oid_as_provider_binding():
    text = AUTH_ROUTER.read_text(encoding="utf-8").lower()

    # Claim interpretation is centralized in resolve_entra_identity(); the
    # router consumes the verified canonical oid returned by that function.
    assert "resolve_entra_identity" in text
    assert 'oid=resolved["oid"]' in text
    assert "provider_subject=oid" in text
    assert "ident.provider_subject=oid" in text
    assert "production_test_student" in text

    # New successful Entra verification must not continue persisting `sub` as
    # the authoritative tenant-scoped user binding.
    assert 'provider_subject=claims.get("sub"' not in text
    assert 'ident.provider_subject=claims.get("sub"' not in text


def test_manual_test_student_is_scoped_to_designated_section_and_team():
    text = ADMIN_ROUTER.read_text(encoding="utf-8").lower()

    for token in (
        "etis_production_test_student_oid",
        "etis_production_test_student_email",
        "etis_production_test_student_id",
        "etis_production_test_section_key",
        "etis_production_test_team_key",
        "provider_subject",
    ):
        assert token in text

    # The exception must remain narrower than an arbitrary external-email path.
    assert "allow gmail.com" not in text
    assert "@gmail.com" not in text


def test_azure_deployment_wires_exact_test_identity_without_hardcoding_it():
    workflow = DEPLOY.read_text(encoding="utf-8")
    bicep = APP_BICEP.read_text(encoding="utf-8")

    required_env = (
        "ETIS_PRODUCTION_TEST_STUDENT_OID",
        "ETIS_PRODUCTION_TEST_STUDENT_EMAIL",
        "ETIS_PRODUCTION_TEST_STUDENT_ID",
        "ETIS_PRODUCTION_TEST_SECTION_KEY",
        "ETIS_PRODUCTION_TEST_TEAM_KEY",
    )

    for name in required_env:
        assert name in workflow
        assert name in bicep

    # Source must carry configuration names, not the actual private test
    # identity selected by the operator.
    combined = (workflow + "\n" + bicep).lower()
    assert "usranger290@gmail.com" not in combined
    assert "a97f7cbb-f60f-4995-afb9-a49220b5ea09" not in combined


def test_application_source_does_not_broadly_allow_gmail():
    app_root = ROOT / "apps" / "api" / "app"
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in app_root.rglob("*.py")
    ).lower()

    assert "@gmail.com" not in combined
    assert 'entra_allowed_domain: str = "gmail.com"' not in combined


def test_production_test_student_is_documented_as_operator_configuration():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    deployment_doc = (
        ROOT / "docs" / "AZURE_DEPLOYMENT.md"
    ).read_text(encoding="utf-8")
    gate17_doc = (
        ROOT / "docs" / "GATE17_PRE_AZURE_GO_NO_GO.md"
    ).read_text(encoding="utf-8")
    acceptance_doc = (
        ROOT
        / "docs"
        / "operations"
        / "POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md"
    ).read_text(encoding="utf-8")

    required = (
        "ETIS_PRODUCTION_TEST_STUDENT_OID",
        "ETIS_PRODUCTION_TEST_STUDENT_EMAIL",
        "ETIS_PRODUCTION_TEST_STUDENT_ID",
        "ETIS_PRODUCTION_TEST_SECTION_KEY",
        "ETIS_PRODUCTION_TEST_TEAM_KEY",
    )

    for name in required:
        assert name in env_example
        assert name in deployment_doc
        assert name in gate17_doc
        assert name in acceptance_doc

    combined = "\n".join(
        (env_example, deployment_doc, gate17_doc, acceptance_doc)
    ).lower()

    # Repository documentation must describe configuration, not embed the
    # operator-selected private test principal.
    assert "usranger290@gmail.com" not in combined
    assert "a97f7cbb-f60f-4995-afb9-a49220b5ea09" not in combined

    assert "exact entra object id" in combined
    assert "designated production-test section" in combined
    assert "designated production-test team" in combined
    assert "does not allow gmail.com generally" in combined


def test_entra_callback_rejects_silent_rebind_of_existing_oid(monkeypatch):
    """
    Once an institutional identity is bound to a verified Entra Object ID,
    a different OID must not take ownership merely by presenting the same
    roster email or student ID.
    """
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        CourseSection,
        CourseTerm,
        InstitutionalIdentity,
        SectionEnrollment,
        User,
    )
    from apps.api.app.routers import auth as auth_router

    old_oid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    new_oid = "11111111-2222-3333-4444-555555555555"

    db = SessionLocal()
    try:
        user = User(
            github_login="luc:student1",
            display_name="Student One",
            role="student",
        )
        db.add(user)
        db.flush()

        term = CourseTerm(
            namespace="COMP330-IDENTITY-BINDING-TEST",
            term_label="Identity Binding Test",
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

        ident = InstitutionalIdentity(
            user_id=user.id,
            student_id="student1",
            institutional_email="student1@luc.edu",
            provider_subject=old_oid,
        )
        db.add(ident)

        db.add(
            SectionEnrollment(
                section_id=section.id,
                user_id=user.id,
                status="active",
            )
        )
        db.commit()

        monkeypatch.setattr(
            auth_router,
            "parse_flow_state",
            lambda state, expected_kind: {"nonce": "expected-nonce"},
        )
        monkeypatch.setattr(
            auth_router,
            "entra_exchange",
            lambda code, expected_nonce: {
                "oid": new_oid,
                "preferred_username": "student1@luc.edu",
                "name": "Student One",
            },
        )
        monkeypatch.setattr(
            auth_router,
            "get_settings",
            lambda: SimpleNamespace(
                etis_production_test_student_id="",
                etis_bootstrap_owner_email="",
                etis_env="development",
            ),
        )

        with pytest.raises(HTTPException) as exc:
            auth_router.entra_callback(
                code="authorization-code",
                state="signed-state",
                db=db,
            )

        assert exc.value.status_code == 409

        db.refresh(ident)
        assert ident.provider_subject == old_oid

    finally:
        db.close()
