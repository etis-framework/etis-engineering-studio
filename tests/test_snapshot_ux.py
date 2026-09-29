"""Saved evidence and an active review must not be mistaken for live HEAD."""

from pathlib import Path
import shutil
import subprocess

import pytest


JS = Path('apps/api/app/static/studio.js').read_text()
HTML = Path('apps/api/app/static/index.html').read_text()
CSS = Path('apps/api/app/static/studio.css').read_text()


def test_saved_snapshot_identity_and_native_lens_disclosure_are_visible():
    assert 'LATEST SAVED EVIDENCE SNAPSHOT' in HTML
    assert 'id="evidenceSnapshotNote"' in HTML
    assert '<details class="evidence-lenses-section">' in HTML
    assert 'Explore other engineering questions' in HTML
    assert '.evidence-lenses-section>summary:focus-visible' in CSS
    assert 'grid-template-columns:minmax(0,1fr) max-content minmax(160px,1fr)' in CSS


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for DOM-state simulation')
def test_saved_snapshot_note_for_no_review_same_review_and_different_review():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const helper=source.slice(source.indexOf('function snapshotCaptureLabel('),source.indexOf('\n const items=',source.indexOf('function renderEngineeringEvidence(')))+'}';
for(const state of ['none','same','different']){
 const elements={'#evidenceWorkspaceTitle':{},'#evidenceWorkspaceMeta':{},'#evidenceSnapshotNote':{}};
 const context={$:key=>elements[key],engineeringEvidenceData:null,
  phaseQuestions:{A2:'Planning'},sessionId:state==='none'?null:91,
  reviewSnapshotId:state==='same'?7:state==='different'?6:null,
  document:{body:{classList:{contains:()=>state!=='none'}}},updateEvidenceReviewActions:()=>{}};
 vm.runInNewContext(helper+'; renderEngineeringEvidence({phase_id:"A2",commit_sha:"abcdef123",coverage:69},{team:{name:"Team"},snapshot_id:7,created_at:"2026-09-29T16:00:00"});',context);
 assert(elements['#evidenceWorkspaceMeta'].textContent.includes('saved snapshot #7'));
 assert(elements['#evidenceWorkspaceMeta'].textContent.includes('commit abcdef12'));
 assert(!elements['#evidenceWorkspaceMeta'].textContent.includes('Invalid Date'));
 const note=elements['#evidenceSnapshotNote'].textContent;
 assert(state==='none'?note.includes('not a live scan'):state==='same'?note.includes('used by your active review'):note.includes('original frozen snapshot'));
}
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


def test_no_use_coaching_preserves_team_attestation_boundary():
    prompt = Path('apps/api/app/services/challenge_engine.py').read_text()
    assert 'Treat that as a team attestation, not independently verified repository proof' in prompt
    assert 'do not invent AI-use entries' in prompt
