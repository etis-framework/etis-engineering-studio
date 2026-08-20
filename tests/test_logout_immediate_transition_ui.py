from pathlib import Path

JS_PATH = Path("apps/api/app/static/studio.js")


def test_successful_logout_forces_immediate_document_reload():
    js = JS_PATH.read_text()

    logout_at = js.index("/auth/logout")
    logout_block = js[logout_at:logout_at + 600]

    assert "window.location.reload()" in logout_block
    assert "window.location.assign('/')" not in logout_block
