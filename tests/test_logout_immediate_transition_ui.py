from pathlib import Path

JS_PATH = Path("apps/api/app/static/studio.js")


def test_successful_logout_switches_ui_before_forced_navigation():
    js = JS_PATH.read_text()

    start = js.index("async function logoutStudio()")
    end = js.index("$('#logoutButton').onclick=logoutStudio;", start)
    block = js[start:end]

    server_success = block.index("if(!r.ok)throw new Error('Sign out failed')")
    hide_app = block.index("$('#appShell').classList.add('hidden')")
    show_login = block.index("$('#loginGate').classList.remove('hidden')")
    replace_nav = block.index("window.location.replace(signedOutUrl.toString())")

    # Never present the signed-out state until the server confirms logout.
    assert server_success < hide_app
    assert server_success < show_login

    # Once logout succeeds, visibly leave the authenticated Studio before
    # depending on browser navigation behavior.
    assert hide_app < replace_nav
    assert show_login < replace_nav

    assert "authenticatedUser=null" in block
    assert "$('#logoutButton').classList.add('hidden')" in block

    # Navigate to a genuinely different URL so Safari cannot treat this as
    # a same-document/same-URL reload.
    assert "new URL('/',window.location.origin)" in block
    assert "searchParams.set('signed_out',String(Date.now()))" in block
    assert "window.location.reload()" not in block
