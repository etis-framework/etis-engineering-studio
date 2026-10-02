import json
from pathlib import Path

import pytest

from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers.reviews import _preferred_evidence_path
from apps.api.app.services.challenge_engine import Challenge, ChallengeEngine
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact


def artifact(path, content, *, provenance='BASELINE', quality='scaffold'):
    return ArtifactFact(
        path=path,
        exists=True,
        provenance=provenance,
        quality=quality,
        summary=f'{path} synthetic artifact',
        content_excerpt=content,
        review_content=content,
        size=len(content.encode()),
        sha256='sha-'+path.replace('/', '-'),
    )


def snapshot_with_findings(phase='A3'):
    arts = [
        artifact('docs/architecture/architecture.md', 'system context components responsibilities interfaces dependencies constraints architecture diagram tradeoffs'),
        artifact('docs/architecture/component-responsibilities.md', 'component responsibility boundary dependency interface'),
        artifact('docs/ai/ai-use-log.md', 'AI use log human verification result action tool purpose artifact activity'),
        artifact('docs/planning/risk-register.md', 'risk likelihood impact mitigation contingency owner status trigger reassessment'),
        artifact('docs/decisions/ADR-000-template.md', 'decision context alternatives rationale consequences owner revisit condition'),
        artifact('docs/team/roles.md', 'owners roles architecture planning risk AI evidence locations acknowledgements'),
        artifact('CONTRIBUTING.md', 'risk architecture decisions AI verification review process owner mitigation testing pull request', quality='reviewable'),
        artifact('.github/workflows/ci.yml', 'manual dispatch placeholder CI test verification failure risk', quality='partial'),
    ]
    ev = build_snapshot(phase, 'team/repo', 'sha', [a.path for a in arts], artifacts=arts)
    ev.findings = [
        {'id':'arch','category':'architecture','title':'Architecture baseline is not demonstrated',
         'statement':'Project-specific system context components interfaces dependencies and tradeoffs are not demonstrated.',
         'significance':'Architecture cannot be reviewed.', 'evidence_refs':['PATH:docs/architecture/architecture.md'], 'suggested_lens':'chief_architect'},
        {'id':'ai','category':'ai_governance','title':'AI-use disclosure is not demonstrated',
         'statement':'AI use or non-use and human verification are not demonstrated.',
         'significance':'AI influence remains untraceable.', 'evidence_refs':['PATH:docs/ai/ai-use-log.md'], 'suggested_lens':'evidence_auditor'},
        {'id':'risk','category':'risk','title':'Risk management is not demonstrated',
         'statement':'No risk with likelihood impact mitigation owner status and trigger is demonstrated.',
         'significance':'Risk remains unmanaged.', 'evidence_refs':['PATH:docs/planning/risk-register.md'], 'suggested_lens':'delivery'},
        {'id':'decision','category':'decision','title':'Architecture decisions are not traceable',
         'statement':'No ADR with alternatives rationale consequences and revisit condition is demonstrated.',
         'significance':'Tradeoffs cannot be defended.', 'evidence_refs':['PATH:docs/decisions/ADR-000-template.md'], 'suggested_lens':'chief_architect'},
    ]
    ev.challenge_candidates = list(ev.findings)
    return ev


def challenge_for(ev, fid):
    f = next(x for x in ev.findings if x['id'] == fid)
    return Challenge(
        id=fid, phase_id=ev.phase_id, lens=f['suggested_lens'], title=f['title'], prompt=f['statement'],
        why_now=f['significance'], evidence_refs=f['evidence_refs'], dimensions=[], expected_move='evidence_boundary_visible',
        noticed=f['statement'], significance=f['significance'], decision_question='What does the evidence support?', finding=f,
    )


@pytest.mark.parametrize('fid,prompt,expected', [
    ('arch', 'We think the architecture evidence is somewhere in the repository. Find it.', 'docs/architecture/architecture.md'),
    ('ai', 'We may have documented AI use or non-use somewhere else. Search the repository.', 'docs/ai/ai-use-log.md'),
    ('risk', 'I know we did this somewhere. Find it.', 'docs/planning/risk-register.md'),
    ('decision', 'Find the strongest architecture decision evidence in the repository.', 'docs/decisions/ADR-000-template.md'),
])
def test_canonical_family_artifact_outranks_generic_distractors(fid, prompt, expected):
    ev = snapshot_with_findings()
    package = EvidencePackageBuilder().build_for_discovery(ev.to_dict(), challenge_for(ev, fid).to_dict(), prompt)
    assert package.relevant_artifacts
    assert package.relevant_artifacts[0]['path'] == expected
    assert package.relevant_artifacts[0]['hydration_status'] == 'FOUND_AND_SUPPLIED'
    assert package.relevant_artifacts[0]['candidate_only'] is True


class FakeDB:
    def __init__(self, ev):
        self.row = type('SnapshotRow', (), {'summary_json': json.dumps(ev.to_dict())})()
    def get(self, model, key):
        assert model is EvidenceSnapshot
        return self.row


def test_server_preferred_target_uses_same_top_hydrated_discovery_candidate():
    ev = snapshot_with_findings()
    state = {'evidence_snapshot_id': 7}
    path = _preferred_evidence_path(
        FakeDB(ev), state, challenge_for(ev, 'risk'), [], 'I know we did this somewhere. Find it.'
    )
    assert path == 'docs/planning/risk-register.md'


def test_missing_remembered_path_plus_search_targets_discovered_architecture_not_missing_path():
    ev = snapshot_with_findings()
    state = {'evidence_snapshot_id': 7}
    path = _preferred_evidence_path(
        FakeDB(ev), state, challenge_for(ev, 'arch'),
        ['PATH:docs/architecture/data-context.md'],
        'I may be remembering the path wrong. Search the frozen repository for architecture evidence.',
    )
    assert path == 'docs/architecture/architecture.md'


def test_valid_exact_path_remains_authoritative_for_ui_target():
    ev = snapshot_with_findings()
    state = {'evidence_snapshot_id': 7}
    path = _preferred_evidence_path(
        FakeDB(ev), state, challenge_for(ev, 'arch'), ['PATH:docs/architecture/component-responsibilities.md'],
        'Inspect this exact file.',
    )
    assert path == 'docs/architecture/component-responsibilities.md'


def test_54_case_phase_repo_student_wargame_keeps_canonical_candidate_hydrated():
    students = {
        'weak': 'I know we did this somewhere. Find it.',
        'average': 'Search the repository for the strongest evidence supporting this finding.',
        'strong': 'Locate equivalent frozen evidence, reject generic process distractors, and distinguish relevance from proof.',
    }
    count = 0
    for phase in ('A1','A2','A3','A4','A5','A6'):
        for repo_strength in ('weak','average','strong'):
            ev = snapshot_with_findings(phase)
            risk = next(a for a in ev.artifacts if a['path'] == 'docs/planning/risk-register.md')
            if repo_strength == 'average':
                risk['provenance'] = 'TEAM_ADAPTED'; risk['quality'] = 'partial'
            elif repo_strength == 'strong':
                risk['provenance'] = 'TEAM_ADDED'; risk['quality'] = 'reviewable'
            for student_strength, prompt in students.items():
                package = EvidencePackageBuilder().build_for_discovery(ev.to_dict(), challenge_for(ev, 'risk').to_dict(), prompt)
                assert package.relevant_artifacts[0]['path'] == 'docs/planning/risk-register.md'
                assert package.relevant_artifacts[0]['hydration_status'] == 'FOUND_AND_SUPPLIED'
                assert package.retrieval['complete_search'] is False
                assert student_strength and repo_strength
                count += 1
    assert count == 54


def test_browser_inspect_uses_server_target_and_has_no_stale_finding_fallback():
    source = Path('apps/api/app/static/studio.js').read_text()
    start = source.index('function reviewerCard(')
    end = source.index('function addTurn(', start)
    card = source[start:end]
    assert "meta.preferred_evidence_path" in card
    assert "findingPrimaryPath(meta.active_finding" not in card
    assert "preferred_evidence_path:reply.preferred_evidence_path" in source
    assert "applyActiveFindingContext(meta.active_finding,meta.active_finding_id,meta.preferred_evidence_path)" in source
