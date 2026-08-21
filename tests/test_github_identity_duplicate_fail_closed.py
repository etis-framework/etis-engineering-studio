from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
from apps.api.app.models import GitHubIdentity, User
from apps.api.app.services.auth import (
    create_session_token,
    parse_flow_state,
    parse_session_token,
)


client=TestClient(app)


def _user(label):
    db=SessionLocal()
    try:
        suffix=uuid4().hex[:10]

        user=User(
            github_login=f"luc:{label}-{suffix}",
            display_name=f"{label.title()} Student",
            role="student",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id

    finally:
        db.close()


def test_same_immutable_github_account_cannot_link_to_two_studio_users(
    monkeypatch,
):
    first_id=_user("first")
    second_id=_user("second")

    db=SessionLocal()
    try:
        db.add(
            GitHubIdentity(
                user_id=first_id,
                github_login="before-rename",
                github_user_id="424242",
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        "apps.api.app.routers.auth.parse_flow_state",
        lambda state,kind: {
            "kind":"github-link",
            "user_id":second_id,
            "session_id":session_id,
        },
    )

    monkeypatch.setattr(
        "apps.api.app.routers.auth.github_exchange",
        lambda code: {
            "login":"after-rename",
            "id":424242,
        },
    )

    token=create_session_token(
        second_id,
        f"second-{second_id}@luc.edu",
        "student",
    )
    session_id=parse_session_token(token)["sid"]

    response=client.get(
        "/auth/github/callback?code=test&state=test",
        headers={"Authorization":f"Bearer {token}"},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "That GitHub identity is already linked to another Studio user"
    )


def test_same_user_can_relink_after_github_login_rename(
    monkeypatch,
):
    user_id=_user("rename")

    db=SessionLocal()
    try:
        db.add(
            GitHubIdentity(
                user_id=user_id,
                github_login="old-login",
                github_user_id="515151",
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        "apps.api.app.routers.auth.parse_flow_state",
        lambda state,kind: {
            "kind":"github-link",
            "user_id":user_id,
            "session_id":session_id,
        },
    )

    monkeypatch.setattr(
        "apps.api.app.routers.auth.github_exchange",
        lambda code: {
            "login":"new-login",
            "id":515151,
        },
    )

    token=create_session_token(
        user_id,
        f"rename-{user_id}@luc.edu",
        "student",
    )
    session_id=parse_session_token(token)["sid"]

    response=client.get(
        "/auth/github/callback?code=test&state=test",
        headers={"Authorization":f"Bearer {token}"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "/?github=linked"

    db=SessionLocal()
    try:
        link=(
            db.query(GitHubIdentity)
            .filter_by(user_id=user_id)
            .one()
        )

        assert link.github_login == "new-login"
        assert link.github_user_id == "515151"

    finally:
        db.close()


def test_github_callback_requires_active_studio_session_before_exchange(
    monkeypatch,
):
    user_id=_user("callback-session")
    exchanged=[]

    monkeypatch.setattr(
        "apps.api.app.routers.auth.parse_flow_state",
        lambda state,kind: {
            "kind":"github-link",
            "user_id":user_id,
            "session_id":999999,
        },
    )
    monkeypatch.setattr(
        "apps.api.app.routers.auth.github_exchange",
        lambda code: exchanged.append(code) or {
            "login":"must-not-run",
            "id":999999,
        },
    )

    response=client.get(
        "/auth/github/callback?code=test&state=test",
        follow_redirects=False,
    )

    # Development's anonymous developer fallback is not a Studio user session
    # and therefore cannot bind a GitHub identity.
    assert response.status_code == 403
    assert exchanged == []


def test_github_callback_rejects_state_for_different_studio_user_before_exchange(
    monkeypatch,
):
    state_user_id=_user("state-user")
    active_user_id=_user("active-user")
    exchanged=[]

    monkeypatch.setattr(
        "apps.api.app.routers.auth.parse_flow_state",
        lambda state,kind: {
            "kind":"github-link",
            "user_id":state_user_id,
            "session_id":active_session_id,
        },
    )
    monkeypatch.setattr(
        "apps.api.app.routers.auth.github_exchange",
        lambda code: exchanged.append(code) or {
            "login":"must-not-run",
            "id":999998,
        },
    )

    token=create_session_token(
        active_user_id,
        f"active-{active_user_id}@luc.edu",
        "student",
    )
    active_session_id=parse_session_token(token)["sid"]

    response=client.get(
        "/auth/github/callback?code=test&state=test",
        headers={"Authorization":f"Bearer {token}"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert "does not match" in response.json()["detail"]
    assert exchanged == []


def test_github_callback_rejects_different_active_session_for_same_user_before_exchange(
    monkeypatch,
):
    user_id=_user("same-user-session")
    initiating_token=create_session_token(
        user_id,
        f"same-user-{user_id}@luc.edu",
        "student",
    )
    initiating_session_id=parse_session_token(initiating_token)["sid"]

    other_token=create_session_token(
        user_id,
        f"same-user-{user_id}@luc.edu",
        "student",
    )
    assert parse_session_token(other_token)["sid"] != initiating_session_id

    exchanged=[]
    monkeypatch.setattr(
        "apps.api.app.routers.auth.parse_flow_state",
        lambda state,kind: {
            "kind":"github-link",
            "user_id":user_id,
            "session_id":initiating_session_id,
        },
    )
    monkeypatch.setattr(
        "apps.api.app.routers.auth.github_exchange",
        lambda code: exchanged.append(code) or {
            "login":"must-not-run",
            "id":999997,
        },
    )

    response=client.get(
        "/auth/github/callback?code=test&state=test",
        headers={"Authorization":f"Bearer {other_token}"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert "initiating Studio session" in response.json()["detail"]
    assert exchanged == []


def test_github_link_state_contains_initiating_studio_session(monkeypatch):
    from types import SimpleNamespace

    user_id=_user("link-state")
    token=create_session_token(
        user_id,
        f"link-state-{user_id}@luc.edu",
        "student",
    )
    session_id=parse_session_token(token)["sid"]
    captured=[]

    monkeypatch.setattr(
        "apps.api.app.routers.auth.get_settings",
        lambda: SimpleNamespace(github_oauth_client_id="client-id"),
    )
    monkeypatch.setattr(
        "apps.api.app.routers.auth.github_authorize_url",
        lambda state: captured.append(state) or "https://github.com/login/oauth/authorize",
    )

    response=client.get(
        "/auth/github/link",
        headers={"Authorization":f"Bearer {token}"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert len(captured) == 1
    pending=parse_flow_state(captured[0],"github-link")
    assert pending["user_id"] == user_id
    assert pending["session_id"] == session_id


def test_github_oauth_scope_is_identity_only(monkeypatch):
    from urllib.parse import parse_qs, urlsplit
    from types import SimpleNamespace

    monkeypatch.setattr(
        "apps.api.app.services.auth.get_settings",
        lambda: SimpleNamespace(
            github_oauth_client_id="client-id",
            github_oauth_redirect_uri="https://studio.example/auth/github/callback",
        ),
    )

    from apps.api.app.services.auth import github_authorize_url

    url=github_authorize_url("state-token")
    query=parse_qs(urlsplit(url).query)

    assert "scope" not in query


def test_database_rejects_duplicate_nonempty_github_account_id():
    first_id=_user("db-first")
    second_id=_user("db-second")

    db=SessionLocal()
    try:
        db.add(
            GitHubIdentity(
                user_id=first_id,
                github_login=f"first-{uuid4().hex[:8]}",
                github_user_id="616161",
            )
        )
        db.commit()

        db.add(
            GitHubIdentity(
                user_id=second_id,
                github_login=f"second-{uuid4().hex[:8]}",
                github_user_id="616161",
            )
        )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError(
                "duplicate immutable GitHub account ID was accepted"
            )

    finally:
        db.close()
