from pathlib import Path

JS=Path("apps/api/app/static/studio.js").read_text()
HTML=Path("apps/api/app/static/index.html").read_text()

def test_visible_actions_and_explanations():
    assert 'id="findCurrentConcernEvidence"' in HTML
    assert 'Find supporting evidence' in HTML
    assert 'searches this frozen snapshot' in HTML
    assert 'Inspect cited source' in HTML
    assert 'class="find-finding-evidence"' in JS
    assert 'data-finding-find=' in JS

def test_discovery_context_does_not_pin_existing_path():
    assert "if(composerContext.kind==='finding_search')return [`FINDING:${composerContext.id}`]" in JS
    block=JS[JS.index('function findingSearchContext('):JS.index('async function findSupportingEvidence(')]
    assert 'evidence_refs:[]' in block
    prompt=JS[JS.index('function findingSearchPrompt('):JS.index('function findingSearchContext(')]
    assert 'Search the frozen repository for equivalent evidence' in prompt
    assert 'strongest candidates' in prompt
    assert 'actually proves and does not prove' in prompt
    assert 'do not treat later work or my assertion as evidence' in prompt

def test_cross_snapshot_draft_and_closed_guards_exist():
    assert 'different frozen snapshot than the active review' in JS
    assert 'Your draft is still here. Send or clear it before asking the reviewer to search.' in JS
    assert "function findingIsClosed(f){return ['corrected','resolved'].includes(findingStatus(f))}" in JS
    assert 'The finding changed in the new repository snapshot.' in JS

def test_no_new_evidence_endpoint_or_lifecycle_mutation():
    block=JS[JS.index('async function findSupportingEvidence('):JS.index('async function actOnFinding(')]
    assert '/api/v1/' not in block
    assert '/disposition' not in block
    assert '/commit' not in block
    assert 'send();' in block
