"""Increment 3 contract checks: advisory findings and frozen context."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'apps/api/app/static/studio.js').read_text()
CSS=(ROOT/'apps/api/app/static/studio.css').read_text()

def test_finding_status_remains_explanatory_not_closed_by_conversation():
    assert 'function findingStatusExplanation(status)' in JS
    assert 'discussing it does not resolve it' in JS
    assert 'does not certify the implementation' in JS
    assert 'finding-state-explanation' in JS

def test_context_label_includes_frozen_snapshot_and_disposition_caveat():
    assert 'Frozen review snapshot #${reviewSnapshotId}' in JS
    assert 'finding-context-explanation' in JS
    assert 'status:findingStatus(f)' in JS

def test_evidence_room_finding_cannot_cross_selected_review_snapshot():
    assert 'function findingSnapshotMatchesActiveReview(f)' in JS
    assert 'Number(reviewSnapshotId)!==Number(engineeringSnapshotId)' in JS
    assert 'if(!findingSnapshotMatchesActiveReview(f))' in JS

def test_existing_navigation_and_governance_are_preserved():
    assert 'function updateRoomOrientation()' in JS
    assert 'async function findSupportingEvidence(f' in JS
    assert 'async function actOnFinding(f' in JS
    assert 'function findingIsClosed(f)' in JS
    assert '.finding-state-explanation' in CSS
