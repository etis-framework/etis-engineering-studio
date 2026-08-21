from types import SimpleNamespace

from apps.api.app.services import evidence as evidence_module


def test_repository_evidence_provider_does_not_use_configured_pat(monkeypatch):
    pat = "ghp_ETISGATE7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    settings = SimpleNamespace(
        github_token=pat,
    )

    monkeypatch.setattr(
        evidence_module,
        "get_settings",
        lambda: settings,
    )

    provider = evidence_module.GitHubEvidenceProvider(
        semantic_assessor=object(),
    )

    # Gate 7 production contract:
    # repository authorization must come from the GitHub App installation,
    # never from a configured personal access token.
    assert "Authorization" not in provider.headers
    assert pat not in str(provider.headers)


from apps.api.app.services import course_admin as course_admin_module


def test_project_name_suggestion_does_not_use_configured_pat(monkeypatch):
    pat = "ghp_ETISGATE7BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    captured = {}

    settings = SimpleNamespace(
        github_token=pat,
        github_app_id="",
        github_app_private_key="",
    )

    class FakeResponse:
        is_success = False

    class FakeClient:
        def __init__(self, *, base_url, headers, timeout, follow_redirects):
            captured["headers"] = dict(headers)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, path):
            return FakeResponse()

    monkeypatch.setattr(
        "apps.api.app.config.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "httpx.Client",
        FakeClient,
    )

    course_admin_module.suggest_project_name("owner/private-repo")

    assert "Authorization" not in captured["headers"]
    assert pat not in str(captured["headers"])


import inspect

from apps.api.app.config import Settings


def test_production_github_access_exposes_no_pat_configuration_surface():
    assert "github_token" not in Settings.model_fields

    parameters = inspect.signature(
        evidence_module.GitHubEvidenceProvider.__init__
    ).parameters

    assert "token" not in parameters


def test_repository_evidence_provider_uses_github_app_installation_token(monkeypatch):
    installation_token = "ghs_ETISGATE7INSTALLATIONTOKEN123456789"
    requested_repositories = []

    class FakeGitHubAppManager:
        def configured(self):
            return True

        def token_for_repo(self, repo_full_name):
            requested_repositories.append(repo_full_name)
            return SimpleNamespace(
                token=installation_token,
                installation_id="123456",
                expires_at=9999999999,
            )

    monkeypatch.setattr(
        evidence_module,
        "github_app_manager",
        FakeGitHubAppManager(),
    )

    provider = evidence_module.GitHubEvidenceProvider(
        semantic_assessor=object(),
    )

    # Base headers never retain repository credentials.
    assert "Authorization" not in provider.headers

    headers = provider._headers_for("etis-framework/private-team-repo")

    assert requested_repositories == [
        "etis-framework/private-team-repo"
    ]
    assert headers["Authorization"] == f"Bearer {installation_token}"

    # Installation credentials are request-scoped, not persisted on the provider.
    assert "Authorization" not in provider.headers
    assert installation_token not in str(provider.headers)


from pathlib import Path


def test_repository_configuration_and_local_docs_expose_no_pat_path():
    env_example = Path(".env.example").read_text()
    local_development = Path("docs/LOCAL_DEVELOPMENT.md").read_text()

    assert "GITHUB_TOKEN" not in env_example
    assert "GITHUB_TOKEN" not in local_development
    assert "GITHUB_APP_ID=" in env_example
    assert "GITHUB_APP_PRIVATE_KEY=" in env_example
    assert "GITHUB_APP_SLUG=" in env_example


from apps.api.app.services.github_app import GitHubAppTokenManager


def test_github_app_requires_both_app_id_and_private_key():
    manager = GitHubAppTokenManager()

    manager.s = SimpleNamespace(
        github_app_id="12345",
        github_app_private_key="",
    )
    assert manager.configured() is False

    manager.s = SimpleNamespace(
        github_app_id="",
        github_app_private_key="private-key",
    )
    assert manager.configured() is False

    manager.s = SimpleNamespace(
        github_app_id="12345",
        github_app_private_key="private-key",
    )
    assert manager.configured() is True


def test_github_app_reuses_valid_cached_installation_token(monkeypatch):
    manager = GitHubAppTokenManager()
    manager.s = SimpleNamespace(
        github_app_id="12345",
        github_app_private_key="private-key",
    )

    calls = []

    cached = SimpleNamespace(
        token="ghs_ETISGATE7CACHEDTOKEN123456789",
        expires_at=5000.0,
        installation_id="777",
    )

    manager._cache["owner/private-repo"] = cached

    monkeypatch.setattr(
        "apps.api.app.services.github_app.time.time",
        lambda: 1000.0,
    )

    def unexpected_lookup(repo_full_name):
        calls.append(repo_full_name)
        raise AssertionError("valid cached token should be reused")

    monkeypatch.setattr(
        manager,
        "installation_for_repo",
        unexpected_lookup,
    )

    result = manager.token_for_repo("owner/private-repo")

    assert result is cached
    assert calls == []
