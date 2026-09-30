"""Finding actions should do what their labels promise without losing drafts."""

from pathlib import Path
import shutil
import subprocess

import pytest


SOURCE = Path('apps/api/app/static/studio.js').read_text()


def test_completed_review_prepares_new_finding_session():
    assert "if(sessionId&&document.body.classList.contains('review-session-active'))" in SOURCE
    assert 'if(sessionId)newReviewHome();' in SOURCE
    assert 'const findings=engineeringEvidenceData?.findings||currentEvidence?.findings||[]' in SOURCE
    assert "selectReviewMode('finding',{findings:available})" in SOURCE
    assert 'if(options.findings){renderFindingPicker(options.findings);updateReviewModeSummary();return}' in SOURCE
    assert 'startReviewAction();' in SOURCE[SOURCE.index('async function configureFindingFromEvidence('):SOURCE.index('function renderEvidenceLensDetail(')]


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
 const waitingChallenge=await scenario('challenge',{pending:true});assert(!waitingChallenge.calls.includes('dispute'));
 const draft=await scenario('discuss',{draft:'My own unfinished answer'});
 assert(!draft.calls.includes('send')&&!draft.calls.includes('context')&&draft.calls.includes('draft-scroll'));
 assert.strictEqual(draft.value,'My own unfinished answer');
 const noSession=await scenario('discuss',{session:null});assert.deepStrictEqual(noSession.calls,['prepare']);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_submitted_challenge_opens_review_and_positions_new_exchange():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('function showSubmittedExchange(');
const fn=source.slice(start,source.indexOf('function updateReadingCue(',start));
const events=[],student={isConnected:true,getBoundingClientRect:()=>({top:510})};
const transcript={scrollTop:50,getBoundingClientRect:()=>({top:100}),scrollIntoView:o=>events.push(['scroll',o.block])};
const ctx={student,els:{transcript},switchView:(v,o)=>events.push(['view',v,o.scroll]),
 requestAnimationFrame:f=>f(),updateReadingCue:()=>events.push(['cue'])};
vm.runInNewContext(fn+';showSubmittedExchange(student)',ctx);
assert.deepStrictEqual(events.map(x=>x[0]),['view','scroll','cue']);
assert.strictEqual(transcript.scrollTop,442);
student.isConnected=false;events.length=0;
vm.runInNewContext(fn+';showSubmittedExchange(student)',ctx);
assert.deepStrictEqual(events.map(x=>x[0]),['view']);
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


def test_evidence_actions_have_distinct_destinations():
    assert 'data-inspect-path' in SOURCE and 'showArtifact(b.dataset.inspectPath' in SOURCE
    assert 'data-focus-path' in SOURCE and 'configureFocusedFromEvidence(`Review the evidence' in SOURCE
    assert 'data-condition-finding' in SOURCE and "'discuss','engineering_evidence'" in SOURCE
    for intent in ('discuss', 'challenge', 'resolve'):
        assert f"configureFindingFromEvidence(b.dataset.finding{intent.capitalize()},'{intent}'" in SOURCE
    focused = SOURCE[SOURCE.index('async function configureFocusedFromEvidence('):SOURCE.index('async function configureFindingFromEvidence(')]
    assert "if(els.response.value.trim())" in focused
    assert "await sending;" in focused
    assert 'startReviewAction();' in focused
    challenge = SOURCE[SOURCE.index('async function disputeEvidence('):SOURCE.index('async function loadInstructor', SOURCE.index('async function disputeEvidence('))]
    assert 'closeEvidenceDispute();\n    showSubmittedExchange(studentTurn);' in challenge


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_ask_reviewer_preserves_draft_or_sends_or_starts_focused_review():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('async function configureFocusedFromEvidence(');
const fn=source.slice(start,source.indexOf('async function configureFindingFromEvidence(',start));
async function scenario({session=12,draft='',busy=false,active=true}={}){
 const events=[],input={value:draft,focus:()=>events.push('focus'),scrollIntoView:()=>events.push('draft-scroll')};
 const purpose={classList:{remove:()=>{}},innerHTML:''};
 const ctx={sessionId:session,pending:busy,finishingReview:false,document:{body:{classList:{contains:()=>active}}},
  els:{response:input,transcript:{scrollIntoView:()=>events.push('transcript-scroll')}},
  switchView:()=>events.push('view'),setMode:()=>events.push('mode'),setComposerContext:()=>events.push('context'),
  updateDraftHint:()=>events.push('hint'),send:async()=>events.push('send'),toast:()=>events.push('toast'),
  requestAnimationFrame:f=>f(),newReviewHome:()=>events.push('home'),
  prepareEntryContext:()=>events.push('entry'),selectReviewMode:async()=>events.push('focused'),
  updateReviewModeSummary:()=>events.push('summary'),startReviewAction:()=>events.push('start'),
  $:s=>s==='#reviewFocus'?{value:''}:purpose,escapeHtml:x=>x};
 await vm.runInNewContext(fn+';configureFocusedFromEvidence("Inspect A2","docs/planning/scope.md")',ctx);
 return {events,value:input.value};
}
(async()=>{
 const draft=await scenario({draft:'Do not erase my question'});
 assert(draft.events.includes('focus')&&!draft.events.includes('send'));
 assert.equal(draft.value,'Do not erase my question');
 const active=await scenario();assert(active.events.includes('send')&&active.events.includes('transcript-scroll'));
 const busy=await scenario({busy:true});assert.deepStrictEqual(busy.events,['toast']);
 const newReview=await scenario({session:null});
 assert(newReview.events.includes('focused')&&newReview.events.includes('start'));
 assert(!newReview.events.includes('send'));
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
const checkbox={checked:false,closest:()=>({classList:{add:()=>calls.push('selected')}})};
const context={fid:finding.id,intent:'discuss',source:'engineering_evidence',
 sessionId:null,pending:false,finishingReview:false,currentView:'evidence',engineeringEvidenceData:{findings:rows},currentEvidence:null,
 selectedFindingIds:selected,currentFindingById:()=>finding,prepareEntryContext:x=>calls.push('context'),
 switchView:()=>calls.push('view'),selectReviewMode:async(m,o)=>{calls.push('mode');assert(selected.has(finding.id));assert(o.findings.includes(finding));},
 $:s=>s==='#reviewSessionPurpose'?purpose:checkbox,CSS:{escape:x=>x},
 updateReviewModeSummary:()=>calls.push('summary'),requestAnimationFrame:()=>{},
 window:{scrollTo:()=>{}},toast:()=>{},escapeHtml:x=>x,
 startReviewAction:()=>{assert(checkbox.checked);assert(selected.has(finding.id));calls.push('start')}};
vm.runInNewContext(fn+';configureFindingFromEvidence(fid,intent,source)',context);
setImmediate(()=>{assert.deepStrictEqual(calls.slice(0,3),['context','view','mode']);assert(selected.has(finding.id));assert(purpose.html.includes(finding.title));assert.equal(calls.filter(x=>x==='start').length,1)});
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_finding_actions_start_once_or_fail_visibly_for_missing_busy_and_active_states():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('async function configureFindingFromEvidence(');
const fn=source.slice(start,source.indexOf('function renderEvidenceLensDetail(',start));
async function scenario(intent,{missing=false,busy=false,active=false,pickerMissing=false,completed=false}={}){
 const calls=[],finding={id:'F-17',title:'Actual finding'},selected=new Set();
 const checkbox={checked:false,closest:()=>({classList:{add:()=>{}}})};
 const ctx={fid:finding.id,intent,source:'engineering_evidence',sessionId:active||completed?91:null,
  pending:busy,finishingReview:false,document:{body:{classList:{contains:()=>active}}},
  currentFindingById:()=>missing?null:finding,engineeringEvidenceData:{findings:[finding]},currentEvidence:null,
  selectedFindingIds:selected,toast:s=>calls.push('toast:'+s),actOnFinding:async()=>calls.push('active'),
  newReviewHome:()=>calls.push('home'),prepareEntryContext:x=>calls.push('entry:'+x.entry_intent),
  switchView:()=>calls.push('view'),selectReviewMode:async()=>calls.push('mode'),
  $:s=>s==='#reviewSessionPurpose'?{classList:{remove:()=>{}},innerHTML:''}:pickerMissing?null:checkbox,
  CSS:{escape:x=>x},updateReviewModeSummary:()=>{},requestAnimationFrame:()=>{},
  window:{scrollTo:()=>{}},escapeHtml:x=>x,startReviewAction:()=>{
   assert(checkbox.checked);assert.deepStrictEqual([...selected],[finding.id]);calls.push('start')
  }};
 await vm.runInNewContext(fn+';configureFindingFromEvidence(fid,intent,source)',ctx);
 return {calls,selected};
}
(async()=>{
 for(const intent of ['discuss','challenge','resolve']){
  const good=await scenario(intent);assert(good.calls.includes('entry:'+intent));assert.equal(good.calls.filter(x=>x==='start').length,1);
  const active=await scenario(intent,{active:true});assert.deepStrictEqual(active.calls,['active']);
 }
 const busy=await scenario('challenge',{busy:true});assert(!busy.calls.includes('start')&&busy.calls[0].startsWith('toast:'));
 const missing=await scenario('discuss',{missing:true});assert(!missing.calls.includes('start')&&missing.calls[0].startsWith('toast:'));
 const noPicker=await scenario('resolve',{pickerMissing:true});assert(!noPicker.calls.includes('start')&&noPicker.selected.size===0);
 const completed=await scenario('discuss',{completed:true});assert(completed.calls[0]==='home'&&completed.calls.includes('start'));
})().catch(e=>{console.error(e);process.exitCode=1});
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
