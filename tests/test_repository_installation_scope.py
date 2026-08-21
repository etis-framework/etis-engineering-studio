from types import SimpleNamespace

import pytest

from apps.api.app.services import evidence as evidence_module
from apps.api.app.services import github_app as github_app_module
from apps.api.app.services.repository_policy import (
    COMP330_STARTER_KIT_REPOSITORY,
    is_configured_production_test_email,
)


def test_production_test_email_exception_is_exact_and_fail_closed():
    assert is_configured_production_test_email(
        " Production-Test@Example.NET ",
        "production-test@example.net",
    )

    assert not is_configured_production_test_email(
        "another@gmail.com",
        "production-test@example.net",
    )

    assert not is_configured_production_test_email(
        "production-test@example.net",
        "",
    )


def test_github_installation_must_use_selected_repositories(
    monkeypatch,
):
    manager=github_app_module.GitHubAppTokenManager()

    manager.s=SimpleNamespace(
        github_app_id="123",
        github_app_private_key="private-key",
    )

    monkeypatch.setattr(
        manager,
        "_app_headers",
        lambda: {"Authorization":"Bearer app-jwt"},
    )

    class Response:
        status_code=200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id":77,
                "repository_selection":"all",
            }

    class Client:
        def __init__(self,**kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self,exc_type,exc,tb):
            return False

        def get(self,path):
            assert path == "/repos/owner/team-repo/installation"
            return Response()

    monkeypatch.setattr(
        github_app_module.httpx,
        "Client",
        Client,
    )

    with pytest.raises(
        RuntimeError,
        match="Only select repositories",
    ):
        manager.installation_for_repo("owner/team-repo")


def test_installation_token_is_scoped_to_exact_repository(
    monkeypatch,
):
    manager=github_app_module.GitHubAppTokenManager()

    manager.s=SimpleNamespace(
        github_app_id="123",
        github_app_private_key="private-key",
    )

    monkeypatch.setattr(
        manager,
        "_app_headers",
        lambda: {"Authorization":"Bearer app-jwt"},
    )

    calls=[]

    class Response:
        def __init__(self,data,status_code=200):
            self._data=data
            self.status_code=status_code

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class Client:
        def __init__(self,**kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self,exc_type,exc,tb):
            return False

        def get(self,path):
            calls.append(("GET",path,None))
            return Response(
                {
                    "id":77,
                    "repository_selection":"selected",
                }
            )

        def post(self,path,json=None):
            calls.append(("POST",path,json))
            return Response(
                {
                    "token":"ghs_exact_repository_token",
                    "repository_selection":"selected",
                    "repositories":[
                        {
                            "full_name":"owner/team-repo",
                        }
                    ],
                },
                status_code=201,
            )

    monkeypatch.setattr(
        github_app_module.httpx,
        "Client",
        Client,
    )

    result=manager.token_for_repo("owner/team-repo")

    assert result.token == "ghs_exact_repository_token"

    assert calls == [
        (
            "GET",
            "/repos/owner/team-repo/installation",
            None,
        ),
        (
            "POST",
            "/app/installations/77/access_tokens",
            {"repositories":["team-repo"]},
        ),
    ]


def test_installation_token_with_wrong_repository_fails_closed(
    monkeypatch,
):
    manager=github_app_module.GitHubAppTokenManager()

    manager.s=SimpleNamespace(
        github_app_id="123",
        github_app_private_key="private-key",
    )

    monkeypatch.setattr(
        manager,
        "_app_headers",
        lambda: {"Authorization":"Bearer app-jwt"},
    )

    class Response:
        def __init__(self,data):
            self._data=data
            self.status_code=200

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class Client:
        def __init__(self,**kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self,exc_type,exc,tb):
            return False

        def get(self,path):
            return Response(
                {
                    "id":77,
                    "repository_selection":"selected",
                }
            )

        def post(self,path,json=None):
            return Response(
                {
                    "token":"ghs_wrong_scope",
                    "repository_selection":"selected",
                    "repositories":[
                        {
                            "full_name":"owner/some-other-repo",
                        }
                    ],
                }
            )

    monkeypatch.setattr(
        github_app_module.httpx,
        "Client",
        Client,
    )

    with pytest.raises(
        RuntimeError,
        match="exact team repository",
    ):
        manager.token_for_repo("owner/team-repo")


def test_known_starter_kit_uses_no_repository_credential(
    monkeypatch,
):
    class Manager:
        def configured(self):
            return True

        def token_for_repo(self,repo_full_name):
            raise AssertionError(
                "public starter fixture must not request "
                "an installation token"
            )

    monkeypatch.setattr(
        evidence_module,
        "github_app_manager",
        Manager(),
    )

    provider=evidence_module.GitHubEvidenceProvider(
        semantic_assessor=object(),
    )

    headers=provider._headers_for(
        COMP330_STARTER_KIT_REPOSITORY
    )

    assert "Authorization" not in headers
