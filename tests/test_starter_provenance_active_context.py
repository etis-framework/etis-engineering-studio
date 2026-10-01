import json

from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers.reviews import _challenge_for_turn, _evidence_context
from apps.api.app.services.challenge_engine import ChallengeEngine, evidence_authority_contract, selected_evidence_focus
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.guidance import guidance_for_topic
from apps.api.app.services.repository_intelligence import ArtifactFact


def artifact(path, content, *, provenance='BASELINE', quality='scaffold'):
    return ArtifactFact(
        path=path, exists=True, provenance=provenance, quality=quality,
        summary='synthetic', content_excerpt=content, review_content=content,
        size=len(content.encode()), sha256='sha-'+path.replace('/', '-'),
    )


def starter_evidence():
    architecture = artifact(
        'docs/architecture/architecture.md',
        '# Architecture\nTODO: describe system purpose, components, interfaces, and trust boundaries.\n',
    )
    ai_log = artifact(
        'docs/ai/ai-use-log.md',
        '# AI Use Log\n| Date | Artifact | Use | Human verification | Outcome |\n|---|---|---|---|---|\n',
    )
    evidence = build_snapshot(
        'A3', 'etis-framework/comp330-f26-starter-kit', 'starter-sha',
        [architecture.path, ai_log.path], artifacts=[architecture, ai_log],
    )
    evidence.findings = [
        {
            'id': 'architecture-empty', 'category': 'artifact_theater',
            'title': 'Architecture package is structurally present but substantively empty',
            'statement': 'Architecture starter artifacts contain structure without project-specific content.',
            'significance': 'The project-specific architecture baseline is not yet demonstrated.',
            'evidence_refs': ['PATH:docs/architecture/architecture.md'],
            'suggested_lens': 'evidence_auditor',
        },
        {
            'id': 'ai-empty', 'category': 'artifact_theater',
            'title': 'AI-use disclosure is defined only as an empty log',
            'statement': 'The starter AI-use log has no project-specific operating record.',
            'significance': 'AI use or non-use is not yet traceable for the reviewed work.',
            'evidence_refs': ['PATH:docs/ai/ai-use-log.md'],
            'suggested_lens': 'evidence_auditor',
        },
    ]
    evidence.challenge_candidates = list(evidence.findings)
    return evidence


def db_for(evidence):
    row = type('SnapshotRow', (), {'summary_json': json.dumps(evidence.to_dict())})()
    class DB:
        def get(self, model, key):
            assert model is EvidenceSnapshot
            return row
    return DB()


def test_selected_finding_replaces_opening_finding_for_turn():
    evidence = starter_evidence()
    opening = ChallengeEngine(ai=object()).start('A3', evidence)
    assert opening.finding['id'] == 'architecture-empty'
    state = {'challenge': opening.to_dict(), 'evidence_snapshot_id': 42}
    challenge = _challenge_for_turn(db_for(evidence), state, ['FINDING:ai-empty', 'PATH:docs/ai/ai-use-log.md'])
    assert challenge.finding['id'] == 'ai-empty'
    assert challenge.title.startswith('AI-use disclosure')
    assert challenge.evidence_refs == ['PATH:docs/ai/ai-use-log.md']


def test_exact_starter_path_keeps_content_under_tight_budget():
    evidence = starter_evidence()
    opening = ChallengeEngine(ai=object()).start('A3', evidence)
    package = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), opening.to_dict(), ['PATH:docs/ai/ai-use-log.md']
    )
    rendered = package.to_prompt_text(max_chars=3000)
    decoded = json.loads(rendered)
    assert decoded['relevant_artifacts'][0]['path'] == 'docs/ai/ai-use-log.md'
    assert decoded['relevant_artifacts'][0]['hydration_status'] == 'FOUND_AND_SUPPLIED'
    assert decoded['relevant_artifacts'][0]['provenance'] == 'BASELINE'
    assert 'AI Use Log' in decoded['relevant_artifacts'][0]['content_excerpt']


def test_selected_focus_calls_baseline_starter_scaffold_not_team_failure():
    evidence = starter_evidence()
    opening = ChallengeEngine(ai=object()).start('A3', evidence)
    rendered = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), opening.to_dict(), ['PATH:docs/architecture/architecture.md']
    ).to_prompt_text()
    focus = selected_evidence_focus(rendered, ['PATH:docs/architecture/architecture.md'])
    assert 'unchanged official COMP 330 starter-kit scaffold' in focus
    assert 'Actual supplied frozen content follows' in focus
    assert 'TODO: describe system purpose' in focus


def test_evidence_authority_contract_preserves_starter_provenance_semantics():
    contract = evidence_authority_contract('Does this file resolve it?', ['PATH:docs/architecture/architecture.md'])
    assert 'BASELINE means unchanged official starter-kit scaffold' in contract
    assert 'Do not describe unchanged BASELINE scaffold as student-authored failure' in contract


def test_ai_finding_does_not_get_unrelated_architecture_guidance_link():
    refs = guidance_for_topic('A3', 'AI-use disclosure is an empty log; what should we do?', 'evidence_boundary_visible', limit=4)
    assert all('Architecture' not in str(item.get('title') or '') for item in refs)


def test_a1_a6_starter_modified_and_team_added_provenance_matrix():
    paths = {
        'A1': 'docs/team/working-agreements.md',
        'A2': 'docs/planning/work-plan.md',
        'A3': 'docs/architecture/architecture.md',
        'A4': 'tests/test_cycle1.py',
        'A5': 'docs/release/acceptance.md',
        'A6': 'docs/operations/runbook.md',
    }
    cases = [
        ('BASELINE', 'scaffold', 'TODO: starter guidance'),
        ('TEAM_ADAPTED', 'partial', 'Owner is assigned; verification TODO.'),
        ('TEAM_ADDED', 'reviewable', 'Owner, result, verification, consequence, and review outcome recorded.'),
    ]
    students = [
        'This exists, so are we done?',
        'What does this actually prove?',
        'This contradicts part of the finding; narrow it to what remains unsupported.',
    ]
    for phase, path in paths.items():
        for provenance, quality, content in cases:
            for student in students:
                art = artifact(path, content, provenance=provenance, quality=quality)
                evidence = build_snapshot(phase, 'team/repo', phase+'-sha', [path], artifacts=[art])
                opening = ChallengeEngine(ai=object()).start(phase, evidence)
                package = EvidencePackageBuilder().build_for_turn(evidence.to_dict(), opening.to_dict(), [f'PATH:{path}'])
                rendered = package.to_prompt_text(max_chars=4000)
                focus = selected_evidence_focus(rendered, [f'PATH:{path}'])
                assert path in focus
                assert provenance in focus
                if provenance == 'BASELINE':
                    assert 'not as student-authored failed work' in focus
                assert content.split('.')[0] in focus
                assert student
