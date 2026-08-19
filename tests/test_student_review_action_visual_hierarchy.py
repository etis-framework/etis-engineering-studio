from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()


def test_blocking_setup_banner_uses_amber_remediation_action():
    assert (
        'id="openReadinessMyTeam" class="secondary setup-required-action"'
        in JS
    )
    assert (
        'class="secondary link-button setup-required-action">'
        'Connect GitHub identity'
        in JS
    )
    assert ".setup-required-action" in CSS


def test_start_review_has_stable_prominent_desktop_footprint():
    assert ".context-actions #newReview" in CSS
    assert "min-width:200px" in CSS
    assert "min-height:46px" in CSS
    assert "font-weight:800" in CSS
