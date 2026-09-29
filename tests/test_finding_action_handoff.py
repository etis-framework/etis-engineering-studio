"""Finding actions should do what their labels promise without losing drafts."""

from pathlib import Path
import shutil
import subprocess

import pytest


SOURCE = Path('apps/api/app/static/studio.js').read_text()


def test_completed_review_prepares_new_finding_session():
    assert "if(sessionId&&document.body.classList.contains('review-session-active'))" in SOURCE
    assert 'if(sessionId)newReviewHome();const findings=' in SOURCE
    assert 'const findings=engineeringEvidenceData?.findings||currentEvidence?.findings||[]' in SOURCE
    assert "selectReviewMode('finding',{findings:available})" in SOURCE
    assert 'if(options.findings){renderFindingPicker(options.findings);updateReviewModeSummary();return}' in SOURCE
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
def test_evidence_handoff_uses_saved_findings_without_repository_analysis():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('async function configureFindingFromEvidence(');
const fn=source.slice(start,source.indexOf('function renderEvidenceLensDetail(',start));
const selected=new Set(),finding={id:'F-12',title:'AI-use disclosure',statement:'Blank form'};
const rows=Array.from({length:12},(_,i)=>({id:'F-'+i,title:'Concern '+i})).concat(finding);
const calls=[],purpose={classList:{remove:()=>{}},set innerHTML(v){this.html=v}};
const context={fid:finding.id,intent:'discuss',source:'engineering_evidence',
 sessionId:null,currentView:'evidence',engineeringEvidenceData:{findings:rows},currentEvidence:null,
 selectedFindingIds:selected,currentFindingById:()=>finding,prepareEntryContext:x=>calls.push('context'),
 switchView:()=>calls.push('view'),selectReviewMode:async(m,o)=>{calls.push('mode');assert(selected.has(finding.id));assert(o.findings.includes(finding));},
 $:s=>s==='#reviewSessionPurpose'?purpose:{checked:true},CSS:{escape:x=>x},
 updateReviewModeSummary:()=>calls.push('summary'),requestAnimationFrame:()=>{},
 window:{scrollTo:()=>{}},toast:()=>{},escapeHtml:x=>x};
vm.runInNewContext(fn+';configureFindingFromEvidence(fid,intent,source)',context);
setImmediate(()=>{assert.deepStrictEqual(calls.slice(0,3),['context','view','mode']);assert(selected.has(finding.id));assert(purpose.html.includes(finding.title))});
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_late_repository_analysis_cannot_replace_evidence_handoff():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('let findingPickerRequestId=0;');
const fn=source.slice(start,source.indexOf('async function prepareLauncherEvidence(',start))
  +source.slice(source.indexOf('async function selectReviewMode(',start),source.indexOf('function renderSessionPurpose(',start));
let complete;const pending=new Promise(resolve=>complete=resolve),shown=[];
const picker={innerHTML:''},panel={classList:{toggle:()=>{}}},choice={dataset:{reviewMode:'finding'},classList:{toggle:()=>{}},setAttribute:()=>{}};
const context={sessionId:null,reviewMode:'board',appRole:'student',currentEvidence:null,
 $$:()=>[choice],$:s=>s==='#findingPicker'?picker:panel,
 studentReviewReadiness:()=>({ready:true}),updateReviewModeSummary:()=>{},
 prepareLauncherEvidence:()=>pending,renderFindingPicker:fs=>shown.push(fs.map(x=>x.id).join(',')),
 renderFindings:()=>shown.push('stale-render'),escapeHtml:x=>x,toast:()=>{}};
const choose=vm.runInNewContext(fn+';selectReviewMode',context);
(async()=>{
 const earlier=choose('finding');
 await choose('finding',{findings:[{id:'selected'}]});
 complete({findings:[{id:'stale'}]});
 await earlier;
 assert.deepStrictEqual(shown,['selected']);
 assert.equal(context.currentEvidence,null);
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
