from pathlib import Path

ROOT=Path("apps/api/app/static")
JS=(ROOT/"studio.js").read_text()
HTML=(ROOT/"index.html").read_text()
CSS=(ROOT/"studio.css").read_text()

def test_review_action_box_is_full_width_and_secondary_panel_is_reduced():
    assert ".review-journey{flex-direction:column;align-items:stretch}" in CSS
    assert 'id="boardPreparation"' not in HTML
    assert 'id="submissionBaseline"' not in HTML
    assert 'OTHER CONCERNS</span>' in HTML
    assert 'OTHER REVIEW CONTEXT' in HTML
    assert "Changes since the previous evidence snapshot" in JS

def test_current_concern_copy_has_structural_title_body_separation():
    block=JS[JS.index("function preparationHTML("):JS.index("function renderChallengeBrief(")]
    assert 'class="preparation-focus-copy"' in block
    assert "<p>${escapeHtml(f.why||'')}</p>" in block
    assert ".preparation-focus-copy>b,.preparation-focus-copy>p" in CSS

def test_evidence_room_removes_duplicate_orientation_copy():
    assert 'class="evidence-room-guide"' not in HTML
    assert "Frozen copy saved ${snapshotCaptureLabel(payload.created_at)}" in JS
    assert "Continue the conversation in Review Room." in JS
    assert "This saved snapshot is used by your active review." not in JS[JS.index("function renderEngineeringEvidence("):JS.index("function updateEvidenceReviewActions(")]

def test_inventory_omits_unavailable_inspect_control():
    render=JS[JS.index("const renderInventory=()=>"):JS.index("$('#engineeringEvidenceFindings').innerHTML")]
    assert "No frozen source available" in render
    assert 'disabled title="No exact frozen artifact is available"' not in render

def test_finding_cards_have_primary_and_secondary_action_hierarchy():
    render=JS[JS.index("$('#engineeringEvidenceFindings').innerHTML"):JS.index("const m=evidence.repository_metrics")]
    assert 'finding-card-primary' in render
    assert 'finding-card-secondary' in render
    assert 'data-finding-discuss' in render
    assert 'data-finding-find' in render
    assert 'class="text-button" data-finding-challenge' in render
    assert 'class="text-button" data-finding-resolve' in render

def test_lens_counts_describe_relationship_not_obligation():
    assert "attention.length+' related findings'" in JS
    assert "attention.length+' to discuss'" not in JS
