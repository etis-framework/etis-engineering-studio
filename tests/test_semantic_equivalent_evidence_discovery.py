import json

from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers.reviews import _evidence_context, _evidence_discovery_signal
from apps.api.app.services.challenge_engine import ChallengeEngine, discovered_evidence_focus
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact


def artifact(path, content, *, provenance='TEAM_ADDED', quality='reviewable'):
    return ArtifactFact(
        path=path, exists=True, provenance=provenance, quality=quality,
        summary='synthetic evidence artifact', content_excerpt=content,
        review_content=content, size=len(content.encode()), sha256='sha-'+path.replace('/', '-'),
    )


def make_evidence(phase, expected, actual=None, *, repo_strength='strong'):
    if actual is None:
        actual = expected.replace('.md', '-alternate.md')
    terms = {
        'A1': 'stakeholder scope ownership working agreement decision authority',
        'A2': 'requirement estimate dependency risk owner acceptance criteria',
        'A3': 'architecture component interface dependency trust boundary decision',
        'A4': 'implementation pull request test integration review result',
        'A5': 'acceptance release verification defect residual risk',
        'A6': 'runbook monitoring recovery incident restore operation',
    }[phase]
    facts = []
    if repo_strength == 'weak':
        facts.append(artifact(actual, 'TODO starter guidance only', provenance='BASELINE', quality='scaffold'))
    elif repo_strength == 'average':
        facts.append(artifact(actual, f'{terms}. Owner assigned; verification remains TODO.', provenance='TEAM_ADAPTED', quality='partial'))
    else:
        facts.append(artifact(actual, f'{terms}. Owner assigned. Dated verification result and review outcome recorded.', provenance='TEAM_ADDED', quality='reviewable'))
        facts.append(artifact('docs/misc/unrelated.md', 'color palette cafeteria parking unrelated notes', quality='reviewable'))
    ev = build_snapshot(phase, 'team/repo', phase+'-sha', [a.path for a in facts], artifacts=facts)
    ev.findings = [{
        'id': 'f-'+phase, 'title': f'{phase} engineering claim is not demonstrated',
        'statement': f'The expected {terms} record is not demonstrated at {expected}.',
        'significance': 'The team needs inspectable evidence for this engineering claim.',
        'evidence_refs': ['PATH:'+expected], 'suggested_lens': 'evidence_auditor',
    }]
    ev.challenge_candidates = list(ev.findings)
    if repo_strength in {'average', 'strong'}:
        ev.claim_support = [{
            'expected_path': expected, 'support_path': actual,
            'support_quote': facts[0].review_content[:120], 'corroborating_evidence': [],
            'support_kind': 'defined' if repo_strength == 'average' else 'demonstrated',
            'judgment': 'okay' if repo_strength == 'average' else 'strong',
        }]
        # Simulate an already validated equivalent location from the frozen review.
        for item in ev.items:
            if item.title == expected:
                item.equivalent_path = actual
    return ev, actual


def fake_db(evidence):
    row = type('SnapshotRow', (), {'summary_json': json.dumps(evidence.to_dict())})()
    class DB:
        def get(self, model, key):
            assert model is EvidenceSnapshot
            return row
    return DB()


def test_discovery_signal_requires_repository_search_intent_and_yields_to_exact_path():
    assert _evidence_discovery_signal('We did this somewhere in the repo. Can you find the evidence?', [])
    assert _evidence_discovery_signal("I don't know which file has the record", [])
    assert _evidence_discovery_signal('Please search the repository for proof of this decision', [])
    assert not _evidence_discovery_signal('What should we do next?', [])
    assert not _evidence_discovery_signal('Does this file resolve it?', ['PATH:docs/x.md'])


def test_validated_equivalent_path_outranks_unrelated_artifact_and_is_not_called_proof():
    evidence, actual = make_evidence('A2', 'docs/planning/estimates.md', 'docs/team/delivery-estimates.md', repo_strength='strong')
    challenge = ChallengeEngine(ai=object()).start('A2', evidence)
    package = EvidencePackageBuilder().build_for_discovery(
        evidence.to_dict(), challenge.to_dict(), 'We did the estimate somewhere else. Can you find it?'
    )
    assert package.retrieval['mode'] == 'bounded_equivalent_evidence_discovery'
    assert package.retrieval['complete_search'] is False
    assert package.relevant_artifacts[0]['path'] == actual
    assert 'validated claim-support relationship' in package.relevant_artifacts[0]['discovery_reasons']
    assert package.relevant_artifacts[0]['candidate_only'] is True
    assert 'not proof' in package.evidence_boundary
    assert all(a['path'] != 'docs/misc/unrelated.md' for a in package.relevant_artifacts)


def test_discovery_context_routes_without_exact_path_and_keeps_active_finding():
    evidence, actual = make_evidence('A3', 'docs/architecture/architecture.md', 'docs/design/system-map.md', repo_strength='strong')
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    state = {'challenge': challenge.to_dict(), 'evidence_snapshot_id': 7}
    text = _evidence_context(
        fake_db(evidence), state, ['FINDING:f-A3'],
        student_text="We documented this, but I don't know which file. Can you find the evidence?",
    )
    package = json.loads(text)
    assert package['retrieval']['mode'] == 'bounded_equivalent_evidence_discovery'
    assert package['challenge']['finding']['id'] == 'f-A3'
    assert package['relevant_artifacts'][0]['path'] == actual


def test_discovery_focus_forces_candidate_inspection_and_non_exhaustive_language():
    evidence, actual = make_evidence('A6', 'docs/operations/runbook.md', 'docs/support/recovery-notes.md', repo_strength='average')
    challenge = ChallengeEngine(ai=object()).start('A6', evidence)
    rendered = EvidencePackageBuilder().build_for_discovery(
        evidence.to_dict(), challenge.to_dict(), 'Find where we documented recovery and operations.'
    ).to_prompt_text()
    focus = discovered_evidence_focus(rendered)
    assert 'ranked candidates' in focus
    assert actual in focus
    assert 'not proof and not a complete repository search' in focus
    assert 'Supplied frozen excerpt' in focus


def test_no_candidate_is_not_proof_of_absence():
    ev = build_snapshot('A3', 'team/repo', 'sha', ['docs/misc/colors.md'], artifacts=[artifact('docs/misc/colors.md', 'palette blue green')])
    ev.findings = [{'id': 'f', 'title': 'Threat model missing', 'statement': 'No threat model is demonstrated.',
                    'significance': 'Security assumptions remain unbounded.', 'evidence_refs': ['PATH:docs/security/threat-model.md']}]
    ev.challenge_candidates = list(ev.findings)
    challenge = ChallengeEngine(ai=object()).start('A3', ev)
    package = EvidencePackageBuilder().build_for_discovery(ev.to_dict(), challenge.to_dict(), 'Can you find our threat model somewhere else?')
    assert package.retrieval['candidate_count'] == 0
    assert 'does not prove' in package.evidence_boundary
    focus = discovered_evidence_focus(package.to_prompt_text())
    assert 'did not find a reviewable candidate' in focus
    assert 'do not claim the evidence does not exist' in focus


def test_a1_a6_weak_average_strong_repo_and_student_matrix_preserves_boundaries():
    expected_paths = {
        'A1': 'docs/team/working-agreements.md',
        'A2': 'docs/planning/estimates.md',
        'A3': 'docs/architecture/architecture.md',
        'A4': 'tests/test_cycle1.py',
        'A5': 'docs/release/acceptance.md',
        'A6': 'docs/operations/runbook.md',
    }
    students = {
        'weak': 'We did this somewhere I think. Can you find the evidence for me?',
        'average': "I know we documented it but I don't know which file. Search the repository and tell me what actually supports the finding.",
        'strong': 'Find equivalent frozen evidence for this claim, reject irrelevant candidates, and distinguish partial from complete support.',
    }
    for phase, expected in expected_paths.items():
        actual = {
            'A1': 'docs/evidence/stakeholder-working-agreement.md',
            'A2': 'docs/evidence/delivery-estimates.md',
            'A3': 'docs/evidence/component-interface-map.md',
            'A4': 'docs/evidence/integration-test-review.md',
            'A5': 'docs/evidence/release-acceptance-verification.md',
            'A6': 'docs/evidence/recovery-runbook.md',
        }[phase]
        for repo_strength in ('weak', 'average', 'strong'):
            evidence, actual_path = make_evidence(phase, expected, actual, repo_strength=repo_strength)
            challenge = ChallengeEngine(ai=object()).start(phase, evidence)
            for student_strength, student_text in students.items():
                package = EvidencePackageBuilder().build_for_discovery(
                    evidence.to_dict(), challenge.to_dict(), student_text
                )
                rendered = package.to_prompt_text(max_chars=9000)
                assert package.commit_sha == phase+'-sha'
                assert package.retrieval['complete_search'] is False
                assert 'not proof' in package.evidence_boundary
                assert actual_path in rendered
                first = package.relevant_artifacts[0]
                assert first['provenance'] == ('BASELINE' if repo_strength == 'weak' else ('TEAM_ADAPTED' if repo_strength == 'average' else 'TEAM_ADDED'))
                assert first['candidate_only'] is True
                assert student_strength
