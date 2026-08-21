import pytest

from apps.api.app.services import github_app as github_app_module


@pytest.mark.parametrize(
    ("owner_type", "login", "account_id"),
    [
        ("User", "student-owner", "101"),
        ("Organization", "course-org", "202"),
    ],
)
def test_repository_owner_identity_resolves_user_or_organization_without_credentials(
    monkeypatch,
    owner_type,
    login,
    account_id,
):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "login": login,
                "id": int(account_id),
                "type": owner_type,
            }

    class FakeClient:
        def __init__(
            self,
            *,
            base_url,
            headers,
            timeout,
            follow_redirects,
        ):
            captured["base_url"] = base_url
            captured["headers"] = dict(headers)
            captured["timeout"] = timeout
            captured["follow_redirects"] = follow_redirects

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, path):
            captured["path"] = path
            return FakeResponse()

    monkeypatch.setattr(
        github_app_module.httpx,
        "Client",
        FakeClient,
    )

    result = github_app_module.repository_owner_identity(
        f"{login}/comp330-f26-team"
    )

    assert result.login == login
    assert result.account_id == account_id
    assert result.owner_type == owner_type

    assert captured["path"] == f"/users/{login}"

    # Ownership lookup is not repo authorization and uses no stored user
    # credential, PAT, OAuth access token, or installation token.
    assert "Authorization" not in captured["headers"]


def test_repository_owner_identity_rejects_missing_github_account(
    monkeypatch,
):
    class FakeResponse:
        status_code = 404

        def raise_for_status(self):
            raise AssertionError(
                "404 should be handled explicitly"
            )

        def json(self):
            return {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, path):
            return FakeResponse()

    monkeypatch.setattr(
        github_app_module.httpx,
        "Client",
        FakeClient,
    )

    with pytest.raises(
        github_app_module.GitHubOwnerResolutionError,
        match="owner account was not found",
    ):
        github_app_module.repository_owner_identity(
            "missing-owner/comp330-f26-team"
        )
