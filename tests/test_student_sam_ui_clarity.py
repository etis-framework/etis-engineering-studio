"""Deterministic student navigation/snapshot war games. No model calls."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path('apps/api/app/static')
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')
JS = (ROOT / 'studio.js').read_text(encoding='utf-8')
CSS = (ROOT / 'studio.css').read_text(encoding='utf-8')


def test_clear_actions_and_help_are_present_in_actual_dom():
    assert 'id="reviewSnapshotContextText"' in HTML
    assert 'id="evidenceSnapshotContextText"' in HTML
    assert 'id="guideStrip"' in HTML
    assert 'id="startAnotherReview"' in HTML
    assert 'id="reviewHistory"' in HTML
    assert HTML.count('data-help-topic="snapshot-lifecycle"') == 2
    assert 'Start another Board Review' in HTML
    assert 'continue an earlier discussion' in JS.lower()
    assert 'latest saved' in JS.lower()
    assert 'openHelp(option.dataset.helpOption)' in JS
    assert 'data-help-option="problem"' in JS
    assert 'data-help-option="room-guide"' in JS
    assert 'data-help-option="quick-start"' in JS
    assert '.snapshot-context' in CSS
    assert '.help-choice-list button:focus-visible' in CSS


def test_draft_guard_is_used_at_both_destructive_context_transitions():
    start = JS[JS.index('function newReviewHome('):JS.index('function prepareEntryContext(', JS.index('function newReviewHome('))]
    resume = JS[JS.index('async function resumeSession('):JS.index('const evidenceLensIds=', JS.index('async function resumeSession('))]
    assert 'if(!preserveDraftBeforeContextChange())return;' in start
    assert 'if(!preserveDraftBeforeContextChange())return;' in resume
    assert 'els.response.value=\'\'' in resume
    assert 'restoreDraft()' in resume
    assert 'sessionStorage.setItem(draftKey()' in JS
    assert 'copy it before switching reviews' in JS.lower()
    assert 'els.phase.onchange=()=>{if(!preserveDraftBeforeContextChange())' in JS
    assert 'openStudioDialog(\'helpOverlay\')' in JS


def test_evidence_response_has_capture_time_without_new_analysis():
    backend = Path('apps/api/app/routers/reviews.py').read_text(encoding='utf-8')
    assert '"snapshot_created_at": snapshot.created_at.isoformat()' in backend
    assert 'reviewSnapshotCapturedAt=d.snapshot_created_at||null' in JS
    assert 'reviewSnapshotCapturedAt=d.snapshot?.created_at||null' in JS
    assert 'engineeringSnapshotCapturedAt=d.created_at||null' in JS
    assert 'Saved evidence was reused' in JS
    assert 'snapshotCaptureLabel' in JS


@pytest.mark.skipif(not shutil.which('node'), reason='Node required for JS simulation')
def test_snapshot_explanation_is_source_bound_for_a1_a6_and_synthetic_personas():
    # 6 phases x 3 repository maturities x 4 participation scenarios; the UI
    # must never assign activity/grades or equate latest saved with GitHub HEAD.
    script = r'''
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('function shortCommit('),end=source.indexOf('function findingContext(',start);
const context=source.slice(start,end);
const date=source.slice(source.indexOf('function snapshotCaptureLabel('),source.indexOf('function renderEngineeringEvidence('));
function el(){return {textContent:''}}
for(const phase of ['A1','A2','A3','A4','A5','A6'])
 for(const maturity of ['weak','average','strong'])
  for(const participation of ['none','weak','average','strong']){
   const review=el(),evidence=el(),rctx=el(),ectx=el();
   const map={'#reviewRoomOrientationDetail':review,'#evidenceRoomOrientationDetail':evidence,'#reviewSnapshotContextText':rctx,'#evidenceSnapshotContextText':ectx};
   const ctx={sessionId:19,reviewSnapshotId:30,engineeringSnapshotId:31,reviewSnapshotCapturedAt:'2026-09-29T09:00:00',engineeringSnapshotCapturedAt:'2026-10-06T09:00:00',reviewSnapshotReused:false,currentPhase:phase,studentContext:null,els:{repo:{value:'course/team'}},currentEvidence:{commit_sha:'abcdef123456',maturity},engineeringEvidenceData:{commit_sha:'987654abcdef',maturity},snapshotCaptureLabel:null,document:{body:{classList:{contains:()=>true}}},$:key=>map[key]||null};
   vm.createContext(ctx);vm.runInContext(date+context+';updateRoomOrientation();',ctx);
   assert(rctx.textContent.includes(phase),phase);
   assert(rctx.textContent.includes('snapshot 30'));
   assert(ectx.textContent.includes('snapshot #31'));
   assert(ectx.textContent.includes('Different from Review #19 snapshot #30'));
   for(const t of [rctx.textContent,ectx.textContent]){
    assert(!/grade|nonparticipat|no contribution|approved for release/i.test(t));
    assert(!/live GitHub HEAD\s*:/i.test(t));
   }
   ctx.engineeringSnapshotId=null;vm.runInContext('updateRoomOrientation()',ctx);
   assert(ectx.textContent.includes('No saved Evidence snapshot shown'));
   assert(evidence.textContent.includes('No saved Evidence snapshot has been loaded'));
   ctx.engineeringSnapshotId=30;vm.runInContext('updateRoomOrientation()',ctx);
   assert(ectx.textContent.includes('Matches Review #19'));
   ctx.reviewSnapshotReused=true;vm.runInContext('updateRoomOrientation()',ctx);
   assert(rctx.textContent.includes('reused saved evidence'));
  }
console.log('PASS 72 A1-A6 × maturity × synthetic participation contexts');
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'PASS 72' in result.stdout


@pytest.mark.skipif(not shutil.which('node'), reason='Node required for JS simulation')
def test_navigation_help_is_local_and_does_not_call_model():
    script = r'''
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const help=source.slice(source.indexOf('const helpTopics='),source.indexOf('function toast('));
const opener=source.slice(source.indexOf('function openHelp('),source.indexOf('function studentGuideKey('));
const title={},content={};let requests=0,opened=0;
const ctx={$:key=>key==='#helpTitle'?title:content,openStudioDialog:()=>opened++,fetch:()=>{requests++}};
vm.createContext(ctx);
vm.runInContext(help+opener+';openHelp("general");openHelp("quick-start");openHelp("snapshot-lifecycle");openHelp("problem");',ctx);
assert.strictEqual(requests,0);assert.strictEqual(opened,4);
assert(content.innerHTML.includes('report')||content.innerHTML.includes('instructor'));
console.log('PASS local help, zero service calls');
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'zero service calls' in result.stdout
