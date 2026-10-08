"""The review launch action stays available across viewport and session states."""

from pathlib import Path
import shutil
import subprocess

import pytest


JS = Path('apps/api/app/static/studio.js').read_text()
HTML = Path('apps/api/app/static/index.html').read_text()
CSS = Path('apps/api/app/static/studio.css').read_text()


def test_context_action_owns_a_responsive_row():
    assert '#studio .professional-context{grid-template-columns:repeat(4,minmax(0,1fr))}' in CSS
    assert '#studio .professional-context .context-actions{grid-column:1/-1;' in CSS
    assert '@media(max-width:1100px){#studio .professional-context{grid-template-columns:repeat(2,minmax(0,1fr))}}' in CSS
    assert '#studio .professional-context{display:grid;grid-template-columns:minmax(0,1fr)}' in CSS
    assert '#studio .professional-context .repo-context{min-width:0}' in CSS
    assert '#studio .professional-context .context-actions #newReview{flex:1;min-width:0;white-space:normal}' in CSS
    assert '.evidence-next-action .preparation-focus>div{display:grid;gap:5px}' in CSS


def test_start_and_choose_actions_are_distinct():
    assert 'id="startBoardFromEvidence" class="primary compact">Choose Board Review →' in HTML
    assert 'id="newReview" class="primary"' in HTML
    assert 'Selecting a review type does not start a session.' in HTML


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for action-state simulation')
def test_evidence_handoff_selects_without_starting_and_active_review_returns():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const fn=source.slice(source.indexOf('function updateEvidenceReviewActions()'),source.indexOf('async function loadEngineeringEvidence()',source.indexOf('function updateEvidenceReviewActions()')));
for(const state of ['new','active','saved']){
 const start={textContent:'',onclick:null},open={classList:{toggle:(key,yes)=>open.hidden=yes}};
 const calls=[];
 const ctx={sessionId:state==='new'?null:37,reviewSnapshotId:null,engineeringSnapshotId:null,document:{body:{classList:{contains:()=>state==='active'}}},
  $:key=>key==='#startBoardFromEvidence'?start:open,
  switchView:v=>calls.push(['view',v]),selectReviewMode:m=>calls.push(['mode',m]),
  newReviewHome:()=>calls.push(['home']),requestAnimationFrame:fn=>fn(),window:{scrollTo:()=>{}},toast:t=>calls.push(['toast',t])};
 vm.runInNewContext(fn+';updateEvidenceReviewActions()',ctx);
 assert.strictEqual(start.textContent,state==='new'?'Choose Board Review →':state==='active'?'Return to selected review':'Start another Board Review');
 start.onclick();
 if(state==='new'){
   assert.deepStrictEqual(calls.slice(0,2),[['view','studio'],['mode','board']]);
   assert(calls.at(-1)[1].includes('Use Start Board Review'));
 }else if(state==='active')assert.deepStrictEqual(calls,[['view','studio']]);
 else assert.deepStrictEqual(calls,[['home']]);
 assert(!calls.some(c=>c[0]==='begin'));
}
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
