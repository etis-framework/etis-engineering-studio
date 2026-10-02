"""The challenge dialog remains understandable across fast and slow responses."""

from pathlib import Path
import subprocess


def test_progress_cues_and_close_behavior_in_both_challenge_modes():
    js = Path('apps/api/app/static/studio.js').read_text()
    html = Path('apps/api/app/static/index.html').read_text()
    css = Path('apps/api/app/static/studio.css').read_text()
    assert 'id="challengeProgress"' in html and 'role="status" aria-live="polite"' in html
    assert 'prefers-reduced-motion:reduce' in css
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const code=source.slice(source.indexOf('let disputePath='),source.indexOf('async function loadHistory(',source.indexOf('let disputePath=')));
function scenario(kind){
 const els={},timers=new Map(),events=[];let tick=0,resolveResponse;
 const response=new Promise(resolve=>resolveResponse=resolve);
 const radios={interpretation:{value:'interpretation',checked:false},evidence:{value:'evidence',checked:false}};
 function el(id){return els[id]??(els[id]={value:'',textContent:'',disabled:false,attrs:{},classList:{values:new Set(['hidden']),add(v){this.values.add(v)},remove(v){this.values.delete(v)},toggle(v,b){b?this.add(v):this.remove(v)}},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},focus(){}})}
 const ctx={sessionId:17,pending:false,currentEvidence:{findings:[{id:'F-1',title:'Planning record absent',evidence_refs:[]}]},
  studioDialogStack:[],openStudioDialog:(id)=>el('#'+id).classList.remove('hidden'),closeStudioDialog:(id)=>el('#'+id).classList.add('hidden'),focusStudioDialog:()=>{},
  $:el,document:{querySelector:q=>q.includes(':checked')?Object.values(radios).find(x=>x.checked):q.includes('value="evidence"')?radios.evidence:radios.interpretation,querySelectorAll:()=>Object.values(radios)},
  setTimeout:(fn,delay)=>{let n=++tick;timers.set(n,{fn,delay});return n},clearTimeout:n=>timers.delete(n),
  toast:s=>events.push(['toast',s]),send:async()=>response,disputeEvidence:async()=>response,
  switchView:s=>events.push(['view',s]),showSubmittedExchange:()=>events.push(['exchange']),
  reviewMutationRequest:()=>({id:'key'}),setPending:()=>{},fetch:async()=>({ok:true,json:async()=>({reply:{lens:'evidence_auditor',text:'Checked.',reviewer:{}}})}),
  addTurn:()=>({id:'turn'}),clearReviewMutation:()=>{},safeErrorMessage:e=>String(e)};
 vm.runInNewContext(code,ctx);
 function fire(delay){for(const [id,t] of [...timers])if(t.delay===delay){timers.delete(id);t.fn()}}
 function open(){ctx.openEvidenceDispute('','F-1');fire(30);radios.interpretation.checked=kind==='interpretation';radios.evidence.checked=kind==='evidence';ctx.updateDisputeKind();el('#evidenceDisputeExplanation').value='We considered another approach.';if(kind==='evidence')el('#evidenceDisputePath').value='docs/planning/notes.md'}
 return {ctx,els,events,open,fire,timers,resolveResponse};
}
(async()=>{
 for(const kind of ['interpretation','evidence']){
  const s=scenario(kind);s.open();
  // Control the actual evidence endpoint without mocking away its progress lifecycle.
  if(kind==='evidence')s.ctx.fetch=async()=>{await new Promise(resolve=>s.resolveResponse=resolve);return {ok:true,json:async()=>({reply:{lens:'evidence_auditor',text:'Checked.',reviewer:{}}})}};
  const first=s.els['#submitEvidenceDispute'].onclick();
  assert(s.els['#submitEvidenceDispute'].disabled);
  assert(!s.els['#submitEvidenceDispute'].classList.values.has('challenge-working'));
  await s.els['#submitEvidenceDispute'].onclick(); // duplicate is ignored
  s.fire(450);assert(s.els['#submitEvidenceDispute'].classList.values.has('challenge-working'));
  assert(s.els['#challengeProgress'].textContent.includes('waiting for a response'));
  s.fire(5000);assert(s.els['#challengeProgress'].textContent.includes('Still waiting'));
  s.ctx.closeEvidenceDispute();assert(s.els['#evidenceDisputeOverlay'].classList.values.has('hidden'));
  assert(s.events.some(e=>e[0]==='toast'&&e[1].includes('still running')));
  s.resolveResponse(kind==='interpretation'?{id:'turn'}:undefined);
  await first;
  assert(!s.els['#submitEvidenceDispute'].disabled);
  assert(s.els['#challengeProgress'].classList.values.has('hidden'));
  assert(!s.timers.size);
  assert(s.events.some(e=>e[0]==='exchange'));
 }
 // A response under 450 ms never flashes a spinner.
 const fast=scenario('interpretation');fast.open();const task=fast.els['#submitEvidenceDispute'].onclick();fast.resolveResponse({id:'turn'});await task;
 assert(!fast.els['#submitEvidenceDispute'].classList.values.has('challenge-working'));
 assert(!fast.timers.size);
 // A failed request after the student closes the dialog reopens the preserved explanation.
 const failed=scenario('interpretation');failed.open();const pending=failed.els['#submitEvidenceDispute'].onclick();failed.ctx.closeEvidenceDispute();failed.resolveResponse(false);await pending;
 assert(!failed.els['#evidenceDisputeOverlay'].classList.values.has('hidden'));
 assert(failed.els['#evidenceDisputeExplanation'].value==='We considered another approach.');
 assert(failed.els['#evidenceDisputeError'].textContent.includes('could not confirm'));
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
