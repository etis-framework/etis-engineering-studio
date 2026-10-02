import json
import subprocess
from pathlib import Path

from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers.reviews import (
    _challenge_for_turn,
    _evidence_context,
    _evidence_discovery_signal,
)
from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.services.evidence import ANALYSIS_CONTRACT, build_snapshot, supports_current_analysis_contract
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact, artifact_from_bytes

FIXTURES = Path('tests/fixtures/starter_subset')


def artifact(path, content, *, provenance='TEAM_ADDED', quality='reviewable'):
    return ArtifactFact(
        path=path, exists=True, provenance=provenance, quality=quality,
        summary='synthetic evidence', content_excerpt=content, review_content=content,
        size=len(content.encode()), sha256='sha-'+path.replace('/', '-'),
    )


def fake_db(evidence):
    row = type('SnapshotRow', (), {'summary_json': json.dumps(evidence.to_dict())})()
    class DB:
        def get(self, model, key):
            assert model is EvidenceSnapshot
            return row
    return DB()


def multi_topic_evidence():
    arts = [
        artifact('docs/architecture/architecture.md', 'starter architecture headings only', provenance='BASELINE', quality='scaffold'),
        artifact('docs/architecture/component-responsibilities.md', 'starter component headings only', provenance='BASELINE', quality='scaffold'),
        artifact('docs/ai/ai-use-log.md', 'empty AI use log table', provenance='BASELINE', quality='scaffold'),
        artifact('docs/planning/risk-register.md', 'Risk register starter table. likelihood impact mitigation owner status reassessment.', provenance='BASELINE', quality='scaffold'),
        artifact('docs/decisions/README.md', 'ADR guidance for decisions alternatives consequences', provenance='BASELINE', quality='scaffold'),
        artifact('CONTRIBUTING.md', 'Pull requests should note remaining risks and follow up work.', provenance='BASELINE', quality='scaffold'),
    ]
    ev = build_snapshot('A3', 'team/repo', 'same-commit', [a.path for a in arts], artifacts=arts)
    ev.findings = [
        {'id':'arch-baseline','category':'architecture','title':'Architecture baseline is not demonstrated',
         'statement':'Project-specific components interfaces dependency direction and trust boundaries are not demonstrated.',
         'significance':'Another engineer cannot evaluate the architecture.',
         'evidence_refs':['PATH:docs/architecture/architecture.md'],'suggested_lens':'chief_architect'},
        {'id':'arch-decisions','category':'decision','title':'Architecture decisions are not traceable',
         'statement':'No accepted ADR with alternatives and consequences is demonstrated.',
         'significance':'Architecture tradeoffs cannot be defended.',
         'evidence_refs':['PATH:docs/decisions/README.md'],'suggested_lens':'chief_architect'},
        {'id':'ai','category':'ai_governance','title':'AI-use disclosure is not demonstrated',
         'statement':'AI use or non-use and human verification are not demonstrated.',
         'significance':'AI influence remains untraceable.',
         'evidence_refs':['PATH:docs/ai/ai-use-log.md'],'suggested_lens':'evidence_auditor'},
        {'id':'risk','category':'risk','title':'Project risk management is not demonstrated',
         'statement':'No specific risk with likelihood impact mitigation owner status and reassessment is demonstrated.',
         'significance':'Delivery risk remains unbounded.',
         'evidence_refs':['PATH:docs/planning/risk-register.md'],'suggested_lens':'delivery'},
    ]
    ev.challenge_candidates = list(ev.findings)
    return ev


def test_analysis_contract_bump_forces_reanalysis_of_same_commit_after_provenance_changes():
    assert ANALYSIS_CONTRACT == 'official_starter_lineage_v4'
    old = {'semantic_review': {'analysis_contract': 'authoritative_turn_context_v3'}}
    assert not supports_current_analysis_contract(old)
    current = {'semantic_review': {'analysis_contract': ANALYSIS_CONTRACT}}
    assert supports_current_analysis_contract(current)


def test_official_starter_fixture_is_baseline_and_carries_lineage_identity():
    for path in ('docs/ai/ai-use-log.md', 'docs/planning/risk-register.md'):
        art = artifact_from_bytes(path, (FIXTURES / path).read_bytes())
        assert art.provenance == 'BASELINE'
        assert art.quality == 'scaffold'
        assert art.starter_lineage == 'official_baseline'
        assert art.starter_baseline_version
        assert 'official comp 330 starter-kit baseline' in art.summary.lower()


def test_mixed_missing_path_plus_explicit_discovery_continues_search():
    ev = multi_topic_evidence()
    opening = ChallengeEngine(ai=object()).start('A3', ev)
    state = {
        'challenge': opening.to_dict(), 'evidence_snapshot_id': 9,
        'active_finding_id': 'arch-baseline',
        'active_finding_by_family': {'architecture':'arch-baseline'},
    }
    assert _evidence_discovery_signal('I do not remember the file. Search the repository for architecture evidence.', ['PATH:docs/architecture/data-context.md'])
    rendered = _evidence_context(
        fake_db(ev), state,
        ['PATH:docs/architecture/data-context.md'],
        student_text='That remembered path may be wrong. Search the repository for equivalent architecture evidence.',
    )
    package = json.loads(rendered)
    assert package['retrieval']['mode'] == 'bounded_equivalent_evidence_discovery'
    assert package['retrieval']['requested_missing_paths'] == ['docs/architecture/data-context.md']
    assert package['relevant_artifacts']
    assert package['relevant_artifacts'][0]['path'].startswith('docs/architecture/')


def test_valid_exact_path_still_wins_even_when_student_also_says_search():
    ev = multi_topic_evidence()
    opening = ChallengeEngine(ai=object()).start('A3', ev)
    state = {'challenge': opening.to_dict(), 'evidence_snapshot_id': 9}
    rendered = _evidence_context(
        fake_db(ev), state,
        ['PATH:docs/architecture/architecture.md'],
        student_text='Inspect this exact file and search the repository too.',
    )
    package = json.loads(rendered)
    assert package.get('retrieval') is None
    assert package['relevant_artifacts'][0]['path'] == 'docs/architecture/architecture.md'
    assert package['relevant_artifacts'][0]['hydration_status'] == 'FOUND_AND_SUPPLIED'


def test_risk_discovery_hydrates_risk_register_ahead_of_generic_contributing_file():
    ev = multi_topic_evidence()
    challenge = ChallengeEngine(ai=object()).start('A3', ev)
    package = EvidencePackageBuilder().build_for_discovery(
        ev.to_dict(), challenge.to_dict(),
        'Search the repository for evidence that we identified and managed meaningful project risks: likelihood impact mitigation owner status and reassessment.'
    )
    paths = [a['path'] for a in package.relevant_artifacts]
    assert 'docs/planning/risk-register.md' in paths
    assert paths.index('docs/planning/risk-register.md') < paths.index('CONTRIBUTING.md') if 'CONTRIBUTING.md' in paths else True
    risk = next(a for a in package.relevant_artifacts if a['path'] == 'docs/planning/risk-register.md')
    assert risk['hydration_status'] == 'FOUND_AND_SUPPLIED'
    assert 'likelihood impact mitigation owner status reassessment' in risk['content_excerpt'].lower()


def test_family_history_returns_to_prior_architecture_finding_when_family_has_multiple_findings():
    ev = multi_topic_evidence()
    opening = ChallengeEngine(ai=object()).start('A3', ev)
    state = {
        'challenge': opening.to_dict(), 'evidence_snapshot_id': 9,
        'active_finding_id': 'ai',
        'active_finding_by_family': {
            'architecture':'arch-baseline', 'ai':'ai', 'risk':'risk', 'decision':'arch-decisions'
        },
    }
    challenge = _challenge_for_turn(fake_db(ev), state, [], student_text='Go back to the architecture finding.')
    assert challenge.id == 'arch-baseline'
    assert challenge.finding['id'] == 'arch-baseline'


def test_a1_a6_repo_and_student_sequence_matrix_keeps_topic_and_evidence_boundaries():
    repo_strengths = ('weak','average','strong')
    student_strengths = {
        'weak': ('risk somewhere find it', 'does this resolve it?'),
        'average': ('Search the repository for risk mitigation owner status and reassessment.', 'What does this actually prove?'),
        'strong': ('Locate equivalent frozen evidence for risk ownership mitigation status and reassessment; reject templates.', 'State what it proves and what remains unsupported.'),
    }
    count = 0
    for phase in ('A1','A2','A3','A4','A5','A6'):
        for repo_strength in repo_strengths:
            ev = multi_topic_evidence()
            ev.phase_id = phase
            for student_strength, (search, followup) in student_strengths.items():
                state = {
                    'challenge': ChallengeEngine(ai=object()).start(phase, ev).to_dict(),
                    'evidence_snapshot_id': 9,
                    'active_finding_id':'risk',
                    'active_finding_by_family':{'architecture':'arch-baseline','risk':'risk','ai':'ai','decision':'arch-decisions'},
                }
                risk = _challenge_for_turn(fake_db(ev), state, [], student_text=search)
                assert risk.id == 'risk'
                vague = _challenge_for_turn(fake_db(ev), state, [], student_text=followup)
                assert vague.id == 'risk'
                package = EvidencePackageBuilder().build_for_discovery(ev.to_dict(), risk.to_dict(), search)
                assert package.retrieval['complete_search'] is False
                assert repo_strength and student_strength
                count += 1
    assert count == 54


def test_browser_active_context_updates_inspect_target_and_clears_stale_guidance():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=source.indexOf('function applyActiveFindingContext(');
const end=source.indexOf('function currentConcernArtifact()',start);
const code=source.slice(start,end);
const nodes={
 '#challengeTitle':{textContent:''}, '#noticedText':{textContent:''}, '#significanceText':{textContent:''},
 '#decisionQuestionText':{textContent:''}, '#relatedGuidance':{innerHTML:'<a>old architecture guidance</a>'}
};
const ctx={currentChallenge:{finding:{id:'ai'},title:'AI'},currentEvidence:{},
 $:sel=>nodes[sel]||null,currentFindingById:id=>null,updateReviewJourney:()=>{ctx.updated=(ctx.updated||0)+1}};
vm.runInNewContext(code,ctx);
ctx.applyActiveFindingContext({id:'risk',title:'Risk finding',statement:'Risk statement',significance:'Risk matters',evidence_refs:['PATH:docs/planning/risk-register.md']},'risk');
assert.equal(ctx.currentChallenge.finding.id,'risk');
assert.equal(ctx.currentChallenge.evidence_refs[0],'PATH:docs/planning/risk-register.md');
assert.equal(nodes['#challengeTitle'].textContent,'Risk finding');
assert(nodes['#relatedGuidance'].innerHTML.includes('current finding'));
ctx.applyActiveFindingContext({id:'arch',title:'Architecture finding',statement:'Arch statement',significance:'Arch matters',evidence_refs:['PATH:docs/architecture/architecture.md']},'arch');
assert.equal(ctx.currentChallenge.finding.id,'arch');
assert.equal(ctx.currentChallenge.evidence_refs[0],'PATH:docs/architecture/architecture.md');
assert.equal(nodes['#challengeTitle'].textContent,'Architecture finding');
'''
    result = subprocess.run(['node','-e',script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
