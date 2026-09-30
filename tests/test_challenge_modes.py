"""Challenge modes preserve student agency and route exact finding context."""

from pathlib import Path
import subprocess


ROOT = Path('apps/api/app/static')


def test_dialog_copy_and_accessible_validation():
    html = (ROOT / 'index.html').read_text()
    css = (ROOT / 'studio.css').read_text()
    assert 'value="interpretation"' in html and 'value="evidence"' in html
    assert 'Example: docs/team/team-charter.md' in html
    assert 'The example above is not an entered path' in html
    assert 'id="evidenceDisputeError"' in html and 'role="alert"' in html
    assert 'aria-describedby="evidenceDisputeError"' in html
    assert '.challenge-dialog [aria-invalid="true"]' in css
    assert '.challenge-dialog{max-height:calc(100vh - 32px);overflow-y:auto}' in css


def test_modes_wargame_synthetic_repositories_and_students():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('let disputePath=');
const end=source.indexOf('async function disputeEvidence(',start);
const code=source.slice(start,end);
async function run({path='',kind,explanation='',draft='',finding=true,accepted=true,busy=false}={}){
 const events=[];
 const elements={};
 function el(id){return elements[id]??(elements[id]={value:'',textContent:'',disabled:false,attrs:{},classList:{values:new Set(['hidden']),add(s){this.values.add(s)},remove(s){this.values.delete(s)},toggle(s,b){b?this.add(s):this.remove(s)}},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},focus(){events.push('focus:'+id)}})}
 const radios={interpretation:{value:'interpretation',checked:false},evidence:{value:'evidence',checked:false}};
 const ctx={sessionId:42,pending:busy,currentEvidence:{findings:finding?[{id:'F-weak',title:'Team commitments not demonstrated',statement:'No operating record',evidence_refs:path?['PATH:'+path]:[]}]:[]},disputeEvidence:async(p,x,f)=>events.push(['evidence',p,x,f]),
  send:async arg=>{events.push(['respond',arg]);return accepted?{id:'student-turn'}:false},
  currentFindingById:()=>finding?{id:'F-weak',title:'Team commitments not demonstrated',statement:'No operating record',evidence_refs:path?['PATH:'+path]:[]}:null,
  switchView:x=>events.push(['view',x]),showSubmittedExchange:x=>events.push(['exchange',x.id]),
  toast:x=>events.push(['toast',x]),
  $:el,document:{querySelector:q=>q.includes(':checked')?Object.values(radios).find(x=>x.checked):q.includes('value="evidence"')?radios.evidence:radios.interpretation,
    querySelectorAll:()=>Object.values(radios)},setTimeout:f=>f()};
 vm.runInNewContext(code,ctx);
 ctx.openEvidenceDispute(path,'F-weak');
 if(kind){Object.values(radios).forEach(r=>r.checked=r.value===kind);ctx.updateDisputeKind()}
 el('#evidenceDisputeExplanation').value=explanation;
 el('#evidenceDisputePath').value=path;
 await el('#submitEvidenceDispute').onclick();
 return {events,els:elements,radios};
}
(async()=>{
 // Weak repo, novice student: a rationale is accepted as a question, not a claim of correction.
 let x=await run({explanation:'We work locally and get along.'});
 assert(x.events.some(e=>e[0]==='respond'&&e[1].evidenceRefs[0]==='FINDING:F-weak'));
 assert(!x.events.some(e=>e[0]==='evidence'));
 assert(x.events.some(e=>e[0]==='exchange'));
 // Average repo: an explicit path correction takes the frozen evidence route.
 x=await run({path:'docs/team/working-agreements.md',kind:'evidence',explanation:'This file records our signed decisions.'});
 assert(x.events.some(e=>e[0]==='evidence'&&e[1]==='docs/team/working-agreements.md'));
 assert(!x.events.some(e=>e[0]==='respond'));
 // Strong repo: alternate path or disagreement may still be routed as a finding challenge.
 x=await run({path:'docs/team/working-agreements.md',kind:'interpretation',explanation:'The dated decisions and revisions support the claim.',draft:'Unsent thought'});
 assert(x.events.some(e=>e[0]==='respond'&&e[1].text.includes('dated decisions')));
 assert(!x.events.some(e=>e[0]==='evidence'));
 // Missing path is persistent inline error, focused on the path, with no network call.
 x=await run({kind:'evidence',explanation:'There is another file.'});
 assert(x.els['#evidenceDisputeError'].textContent.includes('real repository path'));
 assert(x.els['#evidenceDisputePath'].attrs['aria-invalid']==='true');
 assert(!x.events.some(e=>e[0]==='respond'||e[0]==='evidence'));
 // Empty explanation is visibly actionable even if path exists.
 x=await run({path:'docs/team/notes.md',explanation:''});
 assert(x.els['#evidenceDisputeExplanation'].attrs['aria-invalid']==='true');
 // Server failure retains the exact explanation and open form for a retry.
 x=await run({explanation:'I think the interpretation is wrong.',accepted:false});
 assert(x.els['#evidenceDisputeExplanation'].value.includes('interpretation is wrong'));
 assert(!x.els['#evidenceDisputeOverlay'].classList.values.has('hidden'));
 // Stale selected finding and busy session never submit a misleading correction.
 x=await run({explanation:'Reconsider',finding:false});
 assert(x.els['#evidenceDisputeError'].textContent.includes('no longer'));
 x=await run({explanation:'Reconsider',busy:true});
 assert(!x.events.some(e=>e[0]==='respond'||e[0]==='evidence'));
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_challenge_turn_preserves_an_unfinished_composer_draft():
    js = (ROOT / 'studio.js').read_text()
    send = js[js.index('async function send('):js.index('function reviewModeLabel(')]
    assert 'if(!challengeTurn){\n    saveDraft();' in send
    assert 'if(!challengeTurn)clearDraft();' in send
    assert 'if(!challengeTurn)setComposerContext(null);' in send
    assert 'if(!challengeTurn&&!els.response.value)' in send
    assert 'if(challengeTurn)body.evidence_refs=challengeTurn.evidenceRefs;' in send


def test_reviewer_prompt_keeps_weak_and_strong_challenges_grounded():
    from apps.api.app.services.challenge_engine import ChallengeEngine, blank_reasoning
    from apps.api.app.services.evidence import demo_snapshot

    class Probe:
        def __init__(self):
            self.prompts = []

        def available(self):
            return True

        def reviewer_turn(self, system, user):
            self.prompts.append((system, user))
            return {
                'student_intent': 'evidence_dispute', 'understood_points': [],
                'reasoning_updates': {key: False for key in blank_reasoning()},
                'stuck': False, 'frustrated': False, 'needs_direct_teaching': False,
                'next_target': 'evidence_boundary_visible', 'reply': 'Tell me what the dated record shows.',
                'guidance_ids': [], 'handoff_lens': None, 'teach_back': False,
            }

    probe = Probe()
    engine = ChallengeEngine(ai=probe)
    challenge = engine.start('A2', demo_snapshot('A2'))
    for student in ('We work locally, so we did not write this down.',
                    'The dated operating record at docs/team/agreements.md supports this claim.',
                    'I am confused. Can you show me how to challenge this?'):
        engine.converse(challenge, student, blank_reasoning(),
                       evidence_refs=['FINDING:F-team'], evidence_context='Frozen team evidence only',
                       conversation_memory={}, student_name='Sam')
        system, user = probe.prompts[-1]
        assert student in user
        assert 'FINDING:F-team' in user
        assert 'Distinguish what may have happened from what the frozen snapshot demonstrates' in system
        assert 'If the student supplies a real equivalent source, inspect it' in system
