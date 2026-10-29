from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'apps/api/app/static/studio.js').read_text()
HTML = (ROOT / 'apps/api/app/static/index.html').read_text()
CSS = (ROOT / 'apps/api/app/static/studio.css').read_text()


def test_artifact_controls_are_accessible_and_visible():
    assert 'id="evidenceArtifactPath"' in HTML
    assert 'id="inspectEvidenceArtifact"' in HTML
    assert 'id="prepareArtifactReview"' in HTML
    assert 'id="evidenceArtifactRouteFeedback"' in HTML
    assert 'aria-live="polite"' in HTML


def test_artifact_routes_are_wired():
    assert "$('#inspectEvidenceArtifact').onclick=inspectRequestedArtifact" in JS
    assert "$('#prepareArtifactReview').onclick=prepareRequestedArtifactReview" in JS
    assert 'function inspectRequestedArtifact()' in JS
    assert 'async function prepareRequestedArtifactReview()' in JS


def test_active_review_does_not_silently_expand_frozen_scope():
    section = JS.split('async function prepareRequestedArtifactReview(){',1)[1].split('\n}',1)[0]
    assert 'document.body.classList.contains(\'review-session-active\')' in section
    assert 'return;' in section.split('await configureFocusedFromEvidence',1)[0]
    assert 'await configureFocusedFromEvidence' in section
    assert 'reviewSnapshotId' in section


def test_absent_artifact_is_not_claimed_missing_from_repository():
    section = JS.split('function inspectRequestedArtifact(){',1)[1].split('\n}',1)[0]
    assert 'does not prove that the file is absent from GitHub' in section
    assert 'engineeringEvidenceData?.artifacts' in section
    assert 'showArtifact(path,path)' in section


def test_navigation_is_responsive():
    assert '.evidence-artifact-route-controls' in CSS
    assert '@media(max-width:760px)' in CSS
