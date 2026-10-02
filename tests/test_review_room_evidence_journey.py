"""UI contract checks for the two-room coaching path."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps/api/app/static"
JS = (ROOT / "studio.js").read_text()
HTML = (ROOT / "index.html").read_text()
CSS = (ROOT / "studio.css").read_text()


def test_active_review_keeps_coaching_primary_and_evidence_optional():
    assert 'id="reviewJourney"' in HTML
    assert HTML.index('id="reviewJourney"') < HTML.index('id="transcript"')
    assert 'Talk here. Check evidence only when you need it.' in HTML
    assert 'id="inspectCurrentConcern"' in HTML
    assert 'id="browseReviewEvidence"' in HTML
    assert '.review-session-active .review-journey{display:flex}' in CSS
    assert '@media(max-width:900px){.review-journey' in CSS


def test_source_button_stays_on_review_snapshot_and_avoids_missing_artifact():
    body = JS[JS.index('function concernArtifact('):JS.index('function updateReviewJourney()', JS.index('function concernArtifact('))]
    assert "challenge?.finding?.evidence_refs" in body
    assert "challenge?.evidence_refs" in body
    assert "i.title===path&&i.equivalent_path" in body
    assert "return null;" in body
    assert "if(art)showArtifact(art.path,art.path);else switchView('evidence')" in JS
    assert "const snapshotId=currentView==='evidence'?engineeringSnapshotId:reviewSnapshotId" in JS


def test_empty_positive_section_collapses_without_hiding_real_support():
    assert "$('#evidenceSupportedSection').classList.toggle('hidden',!supported.length)" in JS
    assert "supported.map(x=>" in JS
    assert 'id="engineeringEvidenceSummary"' in HTML
    assert "Areas with supported claims</span>" in JS
    assert "start.textContent=active?'Return to active review'" in JS
