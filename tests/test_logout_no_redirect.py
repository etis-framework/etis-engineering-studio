from pathlib import Path


AUTH_PATH = Path("apps/api/app/routers/auth.py")


def _logout_block() -> str:
    source = AUTH_PATH.read_text()
    start = source.index('@router.post("/logout"')
    end = source.index('@router.get("/me")', start)
    return source[start:end]


def test_logout_returns_no_content_instead_of_redirect():
    block = _logout_block()

    assert '@router.post("/logout", status_code=204)' in block
    assert "Response(status_code=204)" in block

    # A POST logout endpoint must not issue a redirect. A 307/308-style
    # redirect can preserve POST and cause the browser to follow it as POST /.
    assert "RedirectResponse" not in block


def test_logout_revokes_session_and_deletes_cookie_before_returning():
    block = _logout_block()

    revoke = block.index("revoke_session_token(token, db)")
    response = block.index("Response(status_code=204)")
    delete_cookie = block.index("response.delete_cookie(COOKIE_NAME, path=\"/\")")
    returned = block.index("return response")

    assert revoke < response < delete_cookie < returned
