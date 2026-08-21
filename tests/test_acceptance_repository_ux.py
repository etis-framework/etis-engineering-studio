from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "apps/api/app/static/index.html").read_text()
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()


def test_command_center_explains_attention_dot_colors():
    assert 'class="attention-legend"' in HTML
    assert "Gold = needs attention" in HTML
    assert "Green = no current attention signal" in HTML
    assert ".attention-legend" in CSS
    assert ".legend-attention" in CSS
    assert ".legend-healthy" in CSS


def test_repository_url_guidance_makes_git_suffix_optional():
    assert "HTTPS GitHub repository URL" in JS
    assert "The <code>.git</code> suffix is optional." in JS
    assert "https://github.com/organization/team-repository" in JS
    assert "Nomination alone does not make the repository trusted evidence." in JS


def test_repository_candidate_submission_has_visible_busy_state():
    assert "Connecting repository…" in JS
    assert "Verifying repository setup with GitHub. This may take a few moments." in JS
    assert "repositoryConnectProgress" in JS
    assert "aria-busy" in JS
    assert ".repository-connect-progress" in CSS


def test_setup_required_and_project_actions_are_clearer():
    assert "Edit project details" in JS
    assert "Confirm / change" not in JS
    assert ".setup-required-label" in CSS
    assert "font-size:10.5px" in CSS


def test_repository_steps_expose_completion_and_current_action_without_color_only():
    assert "STEP 1 OF 2 · OPENED ✓" in JS
    assert "STEP 1 OF 2 · ACTION REQUIRED" in JS
    assert "STEP 2 OF 2 · ACTION REQUIRED" in JS
    assert "STEP 2 OF 2 · LOCKED" in JS
    assert "GitHub may initially show a broader selection." in JS
    assert "Only select repositories" in JS
