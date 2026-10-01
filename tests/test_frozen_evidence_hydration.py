"""Exact selected frozen evidence is hydrated consistently across dialogue routes."""

import json

import pytest

from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers.reviews import _evidence_context
from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact


def artifact(path, *, quality='reviewable', content='project-specific evidence', provenance='TEAM_ADDED'):
    return ArtifactFact(
        path=path,
        exists=True,
        quality=quality,
        provenance=provenance,
        summary='synthetic artifact',
        content_excerpt=content,
        review_content=content,
        size=len(content.encode()),
        sha256='abc123',
    )


def test_exact_selected_path_supplies_content_and_hydration_metadata():
    selected = artifact(
        'docs/ai/ai-use-log.md',
        content='AI use log\n2026-09-30 | architecture review | no material AI use | confirmed by team',
    )
    evidence = build_snapshot('A3', 'team/repo', 'frozen-sha', [selected.path], artifacts=[selected])
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)

    package = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), challenge.to_dict(), [f'PATH:{selected.path}']
    ).to_dict()

    assert package['commit_sha'] == 'frozen-sha'
    assert len(package['relevant_artifacts']) == 1
    supplied = package['relevant_artifacts'][0]
    assert supplied['path'] == selected.path
    assert supplied['hydration_status'] == 'FOUND_AND_SUPPLIED'
    assert 'no material AI use' in supplied['content_excerpt']
    assert supplied['source_sha256'] == 'abc123'


def test_missing_selected_path_is_explicit_not_silently_omitted():
    evidence = build_snapshot('A3', 'team/repo', 'frozen-sha', [], artifacts=[])
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    package = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), challenge.to_dict(), ['PATH:docs/missing.md']
    ).to_dict()

    missing = package['relevant_artifacts'][0]
    assert missing['path'] == 'docs/missing.md'
    assert missing['hydration_status'] == 'PATH_NOT_IN_SNAPSHOT'
    assert missing['content_excerpt'] == ''


@pytest.mark.parametrize('quality,status', [
    ('uninspected', 'FOUND_BUT_UNINSPECTED'),
    ('too_large', 'FOUND_BUT_UNINSPECTED'),
    ('binary', 'FOUND_BUT_UNINSPECTED'),
    ('empty', 'FOUND_BUT_EMPTY'),
])
def test_noninspectable_selected_artifact_never_masquerades_as_supplied(quality, status):
    selected = artifact('docs/evidence/item.md', quality=quality, content='')
    evidence = build_snapshot('A3', 'team/repo', 'frozen-sha', [selected.path], artifacts=[selected])
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    package = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), challenge.to_dict(), [f'PATH:{selected.path}']
    ).to_dict()
    assert package['relevant_artifacts'][0]['hydration_status'] == status


def test_exact_path_precedes_inferred_cross_phase_topic_routing():
    selected = artifact(
        'docs/architecture/architecture.md',
        content='System purpose: route campus requests. Component A owns intake. Interface errors are explicit.',
    )
    a1 = artifact(
        'docs/team/working-agreements.md',
        content='A1 team agreement and decision owner.',
    )
    evidence = build_snapshot('A3', 'team/repo', 'frozen-sha',
                              [selected.path, a1.path], artifacts=[selected, a1])
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    row = type('SnapshotRow', (), {'summary_json': json.dumps(evidence.to_dict())})()

    class DB:
        def get(self, model, key):
            assert model is EvidenceSnapshot and key == 9
            return row

    state = {
        'challenge': challenge.to_dict(),
        'evidence_snapshot_id': 9,
        'conversation_memory': {'coaching_phase': 'A1'},
    }
    encoded = _evidence_context(
        DB(), state,
        evidence_refs=[f'PATH:{selected.path}'],
        student_text='We are not this far yet. Do we have enough to start?',
    )
    package = json.loads(encoded)
    assert package['commit_sha'] == 'frozen-sha'
    assert [a['path'] for a in package['relevant_artifacts']] == [selected.path]
    assert package['relevant_artifacts'][0]['hydration_status'] == 'FOUND_AND_SUPPLIED'
    assert 'Component A owns intake' in package['relevant_artifacts'][0]['content_excerpt']
    assert 'exact selected paths take precedence' in package['evidence_boundary']


def test_exact_path_package_remains_bounded_but_truthful_when_content_is_long():
    selected = artifact('docs/architecture/architecture.md', content='boundary decision\n' * 1500)
    evidence = build_snapshot('A3', 'team/repo', 'frozen-sha', [selected.path], artifacts=[selected])
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    rendered = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), challenge.to_dict(), [f'PATH:{selected.path}']
    ).to_prompt_text(max_chars=5000)
    package = json.loads(rendered)
    assert len(rendered) <= 5000
    if package.get('relevant_artifacts'):
        selected_out = package['relevant_artifacts'][0]
        assert selected_out['path'] == selected.path
        assert selected_out['hydration_status'] == 'FOUND_AND_SUPPLIED'

PHASE_PATHS = {
    'A1': 'docs/team/working-agreements.md',
    'A2': 'docs/planning/work-plan.md',
    'A3': 'docs/architecture/architecture.md',
    'A4': 'tests/test_cycle1.py',
    'A5': 'docs/release/acceptance.md',
    'A6': 'docs/operations/runbook.md',
}

REPO_CASES = {
    'weak': ('scaffold', 'BASELINE', 'TODO: replace this starter guidance with team evidence.'),
    'average': ('partial', 'TEAM_ADAPTED', 'Owner and first decision are recorded; verification remains TODO.'),
    'strong': ('reviewable', 'TEAM_ADDED', 'Owner, decision, rejected alternative, consequence, verification result, and review outcome are recorded.'),
}

STUDENT_CASES = {
    'weak': 'We did this already. Is this file enough?',
    'average': 'Please inspect this file. What does it establish, and what remains?',
    'strong': 'This frozen source contradicts part of the finding. Narrow the interpretation to only what remains unsupported.',
}


@pytest.mark.parametrize('phase', list(PHASE_PATHS))
@pytest.mark.parametrize('repo_level', list(REPO_CASES))
@pytest.mark.parametrize('student_level', list(STUDENT_CASES))
def test_a1_a6_repo_and_student_matrix_preserves_exact_selected_evidence(
    phase, repo_level, student_level
):
    quality, provenance, content = REPO_CASES[repo_level]
    path = PHASE_PATHS[phase]
    selected = artifact(path, quality=quality, provenance=provenance, content=content)
    distracting = artifact(
        'docs/notes/unrelated.md',
        content='Unrelated evidence that must not replace the selected source.',
    )
    evidence = build_snapshot(
        phase, 'team/repo', f'{phase.lower()}-frozen',
        [selected.path, distracting.path], artifacts=[selected, distracting],
    )
    challenge = ChallengeEngine(ai=object()).start(phase, evidence)
    row = type('SnapshotRow', (), {'summary_json': json.dumps(evidence.to_dict())})()

    class DB:
        def get(self, model, key):
            assert model is EvidenceSnapshot and key == 54
            return row

    previous_phase = 'A1' if phase != 'A1' else phase
    state = {
        'challenge': challenge.to_dict(),
        'evidence_snapshot_id': 54,
        'conversation_memory': {'coaching_phase': previous_phase},
    }
    package = json.loads(_evidence_context(
        DB(), state,
        evidence_refs=[f'PATH:{path}'],
        student_text=STUDENT_CASES[student_level],
    ))
    supplied = package['relevant_artifacts'][0]
    assert supplied['path'] == path
    assert supplied['hydration_status'] == 'FOUND_AND_SUPPLIED'
    assert content.split('.')[0] in supplied['content_excerpt']
    assert package['commit_sha'] == f'{phase.lower()}-frozen'
    assert 'grade' not in package['evidence_boundary'].lower()
