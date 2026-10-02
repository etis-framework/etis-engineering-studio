from pathlib import Path

ROOT=Path("apps/api/app/static")
JS=(ROOT/"studio.js").read_text()
CSS=(ROOT/"studio.css").read_text()

def block(start,end):
    return JS[JS.index(start):JS.index(end,JS.index(start))]

def test_reset_hides_stale_other_concerns_before_review():
    reset=block("function resetReview(","function showActiveReviewer(")
    assert "$('#boardReadout')" in reset
    assert "board.classList.add('hidden')" in reset
    assert "board.open=false" in reset

def test_previous_snapshot_summary_is_single_and_reconciled():
    strengths=block("function renderStrengths(","function preparationHTML(")
    assert "appendChild" not in strengths
    render=block("function renderChallengeBrief(","function renderEvidenceSummary(")
    assert "Changes since the previous evidence snapshot" in render
    assert "Findings:" in render
    assert "Evidence areas:" in render
    assert "improved" in render and "regressed" in render
    assert ".board-changes{display:grid;gap:3px}" in CSS

def test_finding_action_does_not_impersonate_student():
    action=block("async function actOnFinding(","function renderFindings(")
    assert "els.response.value=findingStudentPrompt" not in action
    assert "Discuss: ${f.title}" in action
    assert "Help me resolve: ${f.title}" in action
    assert "text:findingStudentPrompt(f,intent)" in action
    assert "evidenceRefs:[`FINDING:${f.id}`" in action
    assert "kind:'finding_action'" in action

def test_ask_reviewer_does_not_impersonate_student():
    focused=block("async function configureFocusedFromEvidence(","async function configureFindingFromEvidence(")
    assert "els.response.value=`I want your honest senior-engineer opinion" not in focused
    assert "displayText:`Ask reviewer about ${actionLabel}`" in focused
    assert "evidenceRefs:path?[`PATH:${path}`]:[]" in focused
    assert "text:`I want your honest senior-engineer opinion" in focused
    assert "kind:'evidence_question'" in focused

def test_aggregate_evidence_uses_single_source_language():
    inventory=block("const renderInventory=()=>","$('#engineeringEvidenceFindings').innerHTML")
    assert "No single frozen source to inspect" in inventory
    assert "No frozen source available" in inventory
    assert "/\\/$/.test(path)" in inventory
    assert "/^GitHub\\b/i.test(path)" in inventory

def test_button_generated_machine_prompt_display_invariant():
    send=block("async function send(","function reviewModeLabel(")
    assert "const displayText=String(challengeTurn?.displayText??text).trim()" in send
    assert "displayText:'Find supporting evidence'" in JS
    assert "displayText:`Ask reviewer about ${actionLabel}`" in JS
    assert "const displayText=intent==='resolve'?" in JS
