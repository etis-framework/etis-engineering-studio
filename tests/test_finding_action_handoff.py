"""Finding actions should do what their labels promise without losing drafts."""

from pathlib import Path
import shutil
import subprocess

import pytest


SOURCE = Path('apps/api/app/static/studio.js').read_text()


def test_completed_review_prepares_new_finding_session():
    assert "if(sessionId&&document.body.classList.contains('review-session-active'))" in SOURCE
    assert 'if(sessionId)newReviewHome();prepareEntryContext(' in SOURCE
    assert 'const findings=engineeringEvidenceData?.findings||currentEvidence?.findings||[]' in SOURCE
    assert "findings.some(x=>x.id===fid)?findings:[f,...findings]" in SOURCE
    assert 'Use Start Finding Review above to begin.' in SOURCE


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_active_discuss_resolve_challenge_pending_and_existing_draft():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const fn=source.slice(source.indexOf('async function actOnFinding('),source.indexOf('function renderFindings(',source.indexOf('async function actOnFinding(')));
const finding={id:'F-2',title:'Missing task evidence'};
async function scenario(intent,{session=37,pending=false,draft=''}={}){
 const calls=[],response={value:draft,focus:()=>calls.push('focus'),scrollIntoView:()=>calls.push('draft-scroll')};
 const ctx={sessionId:session,pending,finishingReview:false,
   els:{response,transcript:{scrollIntoView:()=>calls.push('transcript-scroll')}},
   toast:t=>calls.push('toast:'+t),findingPrimaryPath:()=> 'docs/planning/tasks.md',
   openEvidenceDispute:()=>calls.push('dispute'),configureFindingFromEvidence:async()=>calls.push('prepare'),
   switchView:()=>calls.push('view'),setMode:()=>calls.push('mode'),
   setComposerContext:()=>calls.push('context'),findingContext:()=>({}),
   findingStudentPrompt:()=> 'Please discuss this finding.',updateDraftHint:()=>calls.push('hint'),
   send:async()=>calls.push('send'),requestAnimationFrame:f=>f(),window:{scrollTo:()=>calls.push('top')}};
 await vm.runInNewContext(fn+'; actOnFinding(finding,intent)',{...ctx,finding,intent});
 return {calls,value:response.value};
}
(async()=>{
 const discuss=await scenario('discuss');
 assert(discuss.calls.includes('send')&&discuss.calls.includes('transcript-scroll'));
 assert(!discuss.calls.includes('focus'));
 const resolve=await scenario('resolve');assert(resolve.calls.includes('send'));
 const challenge=await scenario('challenge');assert.deepStrictEqual(challenge.calls,['dispute']);
 const waiting=await scenario('discuss',{pending:true});assert(!waiting.calls.includes('send'));
 const draft=await scenario('discuss',{draft:'My own unfinished answer'});
 assert(!draft.calls.includes('send')&&!draft.calls.includes('context')&&draft.calls.includes('draft-scroll'));
 assert.strictEqual(draft.value,'My own unfinished answer');
 const noSession=await scenario('discuss',{session:null});assert.deepStrictEqual(noSession.calls,['prepare']);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_picker_keeps_selected_finding_beyond_first_eight_visible():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const fn=source.slice(source.indexOf('function renderFindingPicker('),source.indexOf('function findingPrimaryPath(',source.indexOf('function renderFindingPicker(')));
const rows=[],box={set innerHTML(v){rows.length=0},appendChild:v=>rows.push(v)};
const findings=Array.from({length:12},(_,i)=>({id:'F-'+i,title:'Concern '+i,statement:'Evidence '+i}));
const context={selectedFindingIds:new Set(['F-11']),$:(id)=>box,findingStatus:()=> 'open',
 escapeHtml:v=>v,document:{createElement:()=>({querySelector:()=>({}),set innerHTML(v){this.html=v},className:''})}};
vm.runInNewContext(fn+';renderFindingPicker(findings)',{...context,findings});
assert.equal(rows.length,8);
assert(rows[0].html.includes('value="F-11" checked'));
assert(!rows.some(r=>r.html.includes('value="F-8"')));
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
