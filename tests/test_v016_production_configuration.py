from pathlib import Path

import pytest

from apps.api.app.config import Settings


def test_production_settings_reject_default_session_secret():
    with pytest.raises(ValueError, match="ETIS_SESSION_SECRET"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="dev-only-change-me",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        )


def test_production_settings_reject_sqlite_database():
    with pytest.raises(ValueError, match="ETIS_DATABASE_URL"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="sqlite:///./etis-studio.db",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-secret-that-is-not-the-default",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        )


def test_production_settings_reject_generic_entra_organizations_tenant():
    with pytest.raises(ValueError, match="ENTRA_TENANT"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-secret-that-is-not-the-default",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="organizations",
            openai_api_key="sk-proj-ETISGATE9CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        )


def test_production_settings_reject_dev_login():
    with pytest.raises(ValueError, match="ETIS_DEV_LOGIN"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-secret-that-is-not-the-default",
            etis_dev_login=True,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
        )


def test_production_settings_reject_non_https_web_origin():
    with pytest.raises(ValueError, match="ETIS_WEB_ORIGIN"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="http://studio.example.edu",
            etis_session_secret="production-secret-that-is-not-the-default",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
        )


def test_production_settings_reject_non_uuid_entra_tenant():
    with pytest.raises(ValueError, match="ENTRA_TENANT"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-secret-that-is-not-the-default",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="not-a-real-tenant-uuid",
            openai_api_key="sk-proj-ETISGATE9FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
        )


def test_production_settings_reject_short_session_secret():
    with pytest.raises(ValueError, match="ETIS_SESSION_SECRET"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="too-short",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        )


@pytest.mark.parametrize(
    ("client_id", "client_secret"),
    [
        ("", "entra-secret"),
        ("entra-client", ""),
    ],
)
def test_production_settings_require_entra_client_credentials(
    client_id,
    client_secret,
):
    with pytest.raises(ValueError, match="ENTRA_CLIENT"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-session-secret-at-least-32-characters",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id=client_id,
            entra_client_secret=client_secret,
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH",
        )


@pytest.mark.parametrize(
    ("app_id", "private_key"),
    [
        ("", "fake-private-key"),
        ("12345", ""),
    ],
)
def test_production_settings_require_github_app_credentials(
    app_id,
    private_key,
):
    with pytest.raises(ValueError, match="GITHUB_APP"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-session-secret-at-least-32-characters",
            etis_dev_login=False,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id=app_id,
            github_app_private_key=private_key,
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
        )


def test_production_settings_require_openai_key_when_ai_enabled():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-session-secret-at-least-32-characters",
            etis_dev_login=False,
            etis_ai_enabled=True,
            github_oauth_client_id="github-client",
            github_oauth_client_secret="github-secret",
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="",
        )


@pytest.mark.parametrize(
    ("client_id", "client_secret"),
    [
        ("", "github-secret"),
        ("github-client", ""),
    ],
)
def test_production_settings_require_github_oauth_credentials(
    client_id,
    client_secret,
):
    with pytest.raises(ValueError, match="GITHUB_OAUTH"):
        Settings(
            _env_file=None,
            etis_env="production",
            etis_database_url="postgresql://etis:password@db.example.edu/etis",
            etis_web_origin="https://studio.example.edu",
            etis_session_secret="production-session-secret-at-least-32-characters",
            etis_dev_login=False,
            etis_ai_enabled=True,
            github_oauth_client_id=client_id,
            github_oauth_client_secret=client_secret,
            github_oauth_redirect_uri="https://studio.example.edu/auth/github/callback",
            github_app_id="12345",
            github_app_private_key="fake-private-key",
            entra_client_id="entra-client",
            entra_client_secret="entra-secret",
            entra_redirect_uri="https://studio.example.edu/auth/entra/callback",
            entra_tenant="11111111-2222-3333-4444-555555555555",
            openai_api_key="sk-proj-ETISGATE9JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ",
        )


from fastapi.testclient import TestClient

from apps.api.app import main as main_module


def test_readiness_fails_closed_when_database_migration_is_not_current(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "database_readiness",
        lambda: {
            "database_connected": True,
            "migration_current": False,
            "current_revision": "old-revision",
            "head_revision": "a02a1e010b45",
        },
        raising=False,
    )

    with TestClient(main_module.app) as client:
        response = client.get("/ready")

    assert response.status_code == 503

    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["database_connected"] is True
    assert payload["migration_current"] is False
    assert payload["current_revision"] == "old-revision"
    assert payload["head_revision"] == "a02a1e010b45"


from types import SimpleNamespace

from apps.api.app import db as db_module


def test_production_init_db_does_not_create_schema(monkeypatch):
    create_all_calls = []

    monkeypatch.setattr(
        db_module,
        "settings",
        SimpleNamespace(etis_env="production"),
    )
    monkeypatch.setattr(
        db_module.Base.metadata,
        "create_all",
        lambda engine: create_all_calls.append(engine),
    )

    db_module.init_db()

    # Alembic exclusively owns production schema creation/mutation.
    assert create_all_calls == []


def test_readiness_succeeds_when_database_is_connected_and_migration_current(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "database_readiness",
        lambda: {
            "database_connected": True,
            "migration_current": True,
            "current_revision": "a02a1e010b45",
            "head_revision": "a02a1e010b45",
        },
    )

    with TestClient(main_module.app) as client:
        response = client.get("/ready")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database_connected"] is True
    assert payload["migration_current"] is True
    assert payload["current_revision"] == "a02a1e010b45"
    assert payload["head_revision"] == "a02a1e010b45"


def test_openai_production_model_defaults_match_available_project_models():
    root = Path(__file__).resolve().parents[1]

    config_text = (root / "apps" / "api" / "app" / "config.py").read_text(
        encoding="utf-8"
    )
    bicep_text = (root / "infra" / "azure" / "app.bicep").read_text(
        encoding="utf-8"
    )
    env_text = (root / ".env.example").read_text(encoding="utf-8")
    economics_text = (
        root / "docs" / "architecture" / "EVIDENCE_PACKAGES_AND_AI_ECONOMICS.md"
    ).read_text(encoding="utf-8")

    # Student-facing conversation uses the production-available Sol model.
    assert 'openai_model: str = "gpt-5.6-sol"' in config_text
    assert "param openAiModel string = 'gpt-5.6-sol'" in bicep_text
    assert "OPENAI_MODEL=gpt-5.6-sol" in env_text
    assert "default `gpt-5.6-sol`" in economics_text

    # Repository interpretation and selective criticism remain on Luna.
    assert 'openai_repository_model: str = "gpt-5.6-luna"' in config_text
    assert 'openai_critic_model: str = "gpt-5.6-luna"' in config_text
    assert "param openAiRepositoryModel string = 'gpt-5.6-luna'" in bicep_text
    assert "param openAiCriticModel string = 'gpt-5.6-luna'" in bicep_text
