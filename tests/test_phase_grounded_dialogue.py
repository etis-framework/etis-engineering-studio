"""Frozen earlier-phase retrieval and phase-calibrated dialogue scenarios."""

import json

import pytest

from apps.api.app.routers.reviews import _evidence_context
from apps.api.app.services.challenge_engine import ChallengeEngine, blank_reasoning
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact


def artifact(path, quality='reviewable', provenance='TEAM_ADAPTED', content=''):
    return ArtifactFact(path=path, exists=True, quality=quality, provenance=provenance,
                        content_excerpt=content, review_content=content)


@pytest.mark.parametrize('quality,provenance', [
    ('scaffold', 'BASELINE'), ('partial', 'TEAM_ADAPTED'), ('reviewable', 'TEAM_ADDED'),
])
def test_a3_to_a1_retrieves_actual_frozen_launch_sources_without_architecture(quality, provenance):
    launch = artifact('docs/project/launch-context.md', quality, provenance,
                      'We agree the user problem is locating a campus service; the first outcome is a submitted request.')
    roles = artifact('docs/team/roles.md', quality, provenance, 'Decision owner: team lead; issue owner: Maya.')
    architecture = artifact('docs/architecture/architecture.md', content='A3 component boundary and scale assumptions.')
    evidence = build_snapshot('A3', 'team/repo', 'frozen-sha',
                              [launch.path, roles.path, architecture.path], artifacts=[launch, roles, architecture])
    package = EvidencePackageBuilder().build_for_phase(
        evidence.to_dict(), {'title': 'A3 architecture question',
                             'finding': {'statement': 'An A3 issue'}}, 'A1')
    encoded = package.to_prompt_text()
    assert package.topic_phase == 'A1'
    assert package.commit_sha == 'frozen-sha'
    assert launch.path in encoded and roles.path in encoded
    assert architecture.path not in encoded
    assert f'"quality":"{quality}"' in encoded
    assert 'not a complete earlier-phase assessment' in encoded
    assert 'A3 architecture question' not in encoded


def test_a5_to_a3_or_a4_uses_relevant_evidence_and_excludes_release():
    artifacts = [artifact('docs/architecture/decision.md', content='Selected boundary and rationale.'),
                 artifact('src/service.py', content='A controlled implementation.'),
                 artifact('tests/test_service.py', content='A test for the boundary.'),
                 artifact('docs/release/acceptance.md', content='Release acceptance result.')]
    evidence = build_snapshot('A5', 'team/repo', 'same-frozen-sha',
                              [a.path for a in artifacts], artifacts=artifacts).to_dict()
    builder = EvidencePackageBuilder()
    a3 = builder.build_for_phase(evidence, {}, 'A3').to_prompt_text()
    a4 = builder.build_for_phase(evidence, {}, 'A4').to_prompt_text()
    assert 'docs/architecture/decision.md' in a3
    assert 'docs/release/acceptance.md' not in a3
    assert 'src/service.py' in a4 and 'tests/test_service.py' in a4
    assert 'docs/release/acceptance.md' not in a4


def test_long_or_uninspected_earlier_file_stays_bounded_and_uncertain():
    long = artifact('docs/launch/vision.md', 'uninspected', 'UNKNOWN', 'X' * 30000)
    evidence = build_snapshot('A3', 'team/repo', 'sha', [long.path], artifacts=[long]).to_dict()
    result = EvidencePackageBuilder().build_for_phase(evidence, {}, 'A1').to_prompt_text()
    assert len(result) <= 14000
    assert 'uninspected' in result and 'UNKNOWN' in result
    assert 'A filename or polished policy alone does not prove' in result


@pytest.mark.parametrize('gate,topic,source,student,stage', [
    ('A3', 'A1', 'docs/project/launch-context.md', 'We are still at A1. What problem are we solving?', 'ES-101'),
    ('A5', 'A2', 'docs/planning/estimates.md', 'Explain our A2 estimate range.', 'ES-103'),
    ('A5', 'A3', 'docs/architecture/architecture.md', 'Challenge the A3 boundary.', 'ES-104'),
    ('A5', 'A4', 'tests/test_service.py', 'How do our A4 checks show actual behavior?', 'ES-106–ES-109'),
])
def test_phase_appropriate_dialogue_context(gate, topic, source, student, stage):
    class Probe:
        def available(self):
            return True

        def reviewer_turn(self, system, user):
            self.system, self.user = system, user
            return {'student_intent': 'reasoning', 'understood_points': [],
                    'reasoning_updates': blank_reasoning(), 'response_mode': 'teach',
                    'stuck': False, 'frustrated': False, 'needs_direct_teaching': False,
                    'reply': 'Inspect the named frozen source, then record the decision and what people checked.',
                    'guidance_ids': [], 'teach_back': True}

    a = artifact(source, content='A real team decision, its owner, and a recorded verification result.')
    evidence = build_snapshot(gate, 'team/repo', 'sha', [source], artifacts=[a])
    probe = Probe()
    challenge = ChallengeEngine(ai=probe).start(gate, evidence)
    package = EvidencePackageBuilder().build_for_phase(evidence.to_dict(), challenge.to_dict(), topic)
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, student, blank_reasoning(), evidence_context=package.to_prompt_text(),
        conversation_memory={},
    )
    assert reply['coaching_phase'] == topic
    assert source in probe.user
    assert f'For {topic}, use' in probe.system
    assert all(topic in ref['phase_ids'] for ref in reply['guidance_refs'])
    assert stage in {ref['stage'] for ref in reply['guidance_refs']}
    if topic == 'A1':
        assert 'A1 project launch is not production acceptance' in probe.system


def test_router_retrieval_uses_frozen_snapshot_and_topic_memory():
    from apps.api.app.models import EvidenceSnapshot

    a = artifact('docs/team/working-agreements.md', content='Team decision owner and escalation record.')
    evidence = build_snapshot('A3', 'team/repo', 'frozen', [a.path], artifacts=[a])
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    row = type('SnapshotRow', (), {'summary_json': json.dumps(evidence.to_dict())})()

    class DB:
        def get(self, model, key):
            assert model is EvidenceSnapshot and key == 7
            return row

    state = {'challenge': challenge.to_dict(), 'evidence_snapshot_id': 7,
             'conversation_memory': {'coaching_phase': 'A1'}}
    package = json.loads(_evidence_context(DB(), state, student_text='What would evidence of that look like?'))
    assert package['topic_phase'] == 'A1'
    assert a.path in {x['path'] for x in package['relevant_artifacts']}
    assert package['commit_sha'] == 'frozen'


def test_equivalent_a1_evidence_in_unusual_docs_location_is_discovered():
    equivalent = artifact('docs/notes/overview.md', content=(
        'Our stakeholder is the campus help desk. The problem is lost requests. '
        'Success means the first request reaches an owner within one day.'))
    architecture = artifact('docs/architecture/design.md', content='Component interface boundary.')
    evidence = build_snapshot('A3', 'team/repo', 'frozen',
                              [equivalent.path, architecture.path], artifacts=[equivalent, architecture])
    result = EvidencePackageBuilder().build_for_phase(evidence.to_dict(), {}, 'A1').to_prompt_text()
    assert equivalent.path in result
    assert architecture.path not in result
    assert 'Success means' in result


@pytest.mark.parametrize('maturity,student,expected_path', [
    ('weak', 'I am stuck on A1; show me what launch evidence looks like.', 'docs/team/roles.md'),
    ('average', 'We wrote A1 context. What is still uncertain?', 'docs/project/launch.md'),
    ('strong', 'I challenge your A1 reading; our stakeholder signed off. Check this.', 'docs/notes/overview.md'),
])
def test_student_skill_and_repository_maturity_keep_evidence_boundary(maturity, student, expected_path):
    files = {
        'weak': [artifact('docs/team/roles.md', 'scaffold', 'BASELINE', 'Name team roles here.')],
        'average': [artifact('docs/project/launch.md', 'partial', 'TEAM_ADAPTED',
                             'Stakeholder and problem are agreed; success measure pending.')],
        'strong': [artifact('docs/notes/overview.md', 'reviewable', 'TEAM_ADDED',
                            'Stakeholder approved the problem and scope. Success is 12 resolved requests.')],
    }[maturity]
    evidence = build_snapshot('A3', 'team/repo', 'frozen', [a.path for a in files], artifacts=files)
    package = EvidencePackageBuilder().build_for_phase(evidence.to_dict(), {}, 'A1').to_prompt_text()
    assert expected_path in package
    assert 'not a complete earlier-phase assessment' in package
    assert 'grade' not in package.lower()

    class Probe:
        def available(self):
            return True

        def reviewer_turn(self, system, user):
            self.user, self.system = user, system
            return {'student_intent': 'stuck' if maturity == 'weak' else 'reasoning',
                    'understood_points': [], 'reasoning_updates': blank_reasoning(),
                    'response_mode': 'teach' if maturity == 'weak' else 'conversation',
                    'stuck': maturity == 'weak', 'frustrated': False,
                    'needs_direct_teaching': maturity == 'weak',
                    'reply': 'Here is what this bounded source shows, and one useful next action.',
                    'guidance_ids': [], 'teach_back': maturity == 'weak'}

    probe = Probe()
    challenge = ChallengeEngine(ai=probe).start('A3', evidence)
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, student, blank_reasoning(), evidence_context=package,
        conversation_memory={},
    )
    assert reply['coaching_phase'] == 'A1'
    assert expected_path in probe.user
    assert 'production acceptance' in probe.system
    if maturity == 'weak':
        assert reply['kind'] == 'teaching'
