from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import app


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
SETUP_JS = (ROOT / "apps/api/app/static/github-setup-complete.js").read_text()
SETUP_HTML = (ROOT / "apps/api/app/static/github-setup-complete.html").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()

client = TestClient(app)


def test_meaningful_studio_navigation_uses_browser_history():
    assert "window.history[replace?'replaceState':'pushState']" in JS
    assert "window.addEventListener('popstate'" in JS
    assert "function navigationState()" in JS
    assert "function navigationUrl(state)" in JS
    assert "function restoreNavigationState(state)" in JS
    assert "initializeBrowserNavigation()" in JS

    for key in ["view", "section", "team", "review", "session"]:
        assert f"url.searchParams.set('{key}'" in JS or f"url.searchParams.set(\"{key}\"" in JS


def test_section_context_is_preserved_without_cluttering_back_history():
    assert "setInstructorSectionContext(value,{reload=true}={})" in JS
    assert "recordNavigationState({replace:true})" in JS
    assert "sessionStorage.setItem(instructorSectionStorageKey()" in JS


def test_team_and_review_drilldowns_are_single_meaningful_history_entries():
    assert "loadTeamDetail(t.id,{focus:true,history:true})" in JS
    assert "switchView('instructor',{history:false});loadTeamDetail(Number(b.dataset.teamOpen),{focus:true,history:true})" in JS
    assert "switchView('instructorReviews',{history:false})" in JS
    assert "loadInstructorReviewDetail(Number(button.dataset.teamActiveReview),{history:true})" in JS
    assert "{history:true}" in JS
    assert "currentInstructorTeamId" in JS
    assert "currentInstructorReviewSessionId" in JS


def test_github_setup_completion_route_is_informational_not_verification():
    response = client.get(
        "/github/setup-complete?installation_id=999999&setup_action=update"
    )
    assert response.status_code == 200
    assert "GITHUB AUTHORIZATION COMPLETE" in response.text
    assert "complete Step 2 to verify the exact nominated repository" in response.text
    assert "/assets/github-setup-complete.js" in response.text
    assert "999999" not in response.text
    assert "installation_id" not in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]


def test_github_setup_completion_notifies_existing_studio_tab_and_has_deterministic_return():
    assert "etis:github-setup-complete" in SETUP_JS
    assert "etis-github-setup" in SETUP_JS
    assert "localStorage.setItem" in SETUP_JS
    assert "BroadcastChannel" in SETUP_JS
    assert "github-setup-return-request" in SETUP_JS
    assert "github-setup-return-ack" in SETUP_JS
    assert "window.location.assign(STUDIO_URL)" in SETUP_JS
    assert "window.close()" in SETUP_JS
    assert "window.setTimeout(closeSetupTab,1500)" not in SETUP_JS
    assert 'href="/?view=myteam"' in SETUP_HTML
    assert "Return to ETIS Engineering Studio" in SETUP_HTML
    assert "Close this tab" in SETUP_HTML
    assert "You may also close this tab" in SETUP_HTML
    assert "github-setup-return-request" in JS
    assert "github-setup-return-ack" in JS
    assert "window.focus()" in JS
    assert "document.hasFocus()" in JS
    assert "handleGitHubSetupComplete" in JS
    assert "await loadStudentContext(authenticatedUser.id)" in JS
    assert "Verify the exact repository when you are ready." in JS
    assert ".github-setup-complete-page" in CSS
