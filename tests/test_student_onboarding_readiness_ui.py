from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "apps/api/app/static/index.html").read_text()
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()


def test_student_review_room_surfaces_setup_readiness():
    assert 'id="studentReadiness"' in HTML
    assert 'id="newReview" class="primary" disabled' in HTML
    assert "function studentReviewReadiness()" in JS
    assert "function renderStudentReadiness()" in JS
    assert "ob.github_identity" in JS
    assert "ob.repository_connected" in JS
    assert "Finish GitHub setup before your first review" in JS
    assert "Connect your team repository before starting a review" in JS
    assert "Only one teammate needs to connect and verify the repository" in JS


def test_review_start_is_blocked_until_student_setup_is_ready():
    assert "if(appRole==='student'&&!readiness.ready)" in JS
    assert "Setup required before review" in JS
    assert "btn.disabled=true" in JS
    assert "switchView('myteam')" in JS
    assert "#newReview:disabled" in CSS
    assert "Finish setup in My Team before Studio prepares repository findings." in JS


def test_engineering_evidence_routes_incomplete_setup_to_my_team():
    assert "Finish setup before Engineering Evidence can be prepared." in JS
    assert 'id="evidenceOpenSetup"' in JS
    assert "Open My Team" in JS


def test_authenticated_shell_exposes_csrf_protected_logout():
    assert 'id="logoutButton"' in HTML
    assert "async function logoutStudio()" in JS
    assert "fetch('/auth/logout',{method:'POST'})" in JS
    assert "$('#logoutButton').classList.remove('hidden')" in JS
    assert "csrfToken=null" in JS
