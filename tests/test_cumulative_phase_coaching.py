"""Synthetic maturity and student dialogue checks for cumulative coaching."""

import pytest

from apps.api.app.services.cumulative_phase import coaching_phase, foundation_concern
from apps.api.app.services.challenge_engine import ChallengeEngine, blank_reasoning, earlier_topic_drift
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.repository_intelligence import ArtifactFact


def art(path, quality='reviewable', provenance='TEAM_ADAPTED'):
    return ArtifactFact(path=path, exists=True, quality=quality, provenance=provenance)


@pytest.mark.parametrize('gate,repo,expected', [
    ('A3', [art('README.md','scaffold','BASELINE'), art('docs/team/roles.md','scaffold','BASELINE')], 'A1'),
    ('A5', [art('README.md'), art('docs/team/roles.md'), art('docs/planning/scope.md'),
            art('docs/planning/risk.md'), art('docs/architecture/architecture.md'),
            art('docs/decisions/architecture.md'), art('src/app.py','scaffold','BASELINE'),
            art('tests/test_app.py','scaffold','BASELINE')], 'A4'),
    ('A5', [art('README.md'), art('docs/team/roles.md'), art('docs/planning/scope.md'),
            art('docs/planning/risk.md'), art('docs/architecture/architecture.md'),
            art('docs/decisions/architecture.md'), art('src/app.py'), art('tests/test_app.py')], None),
    ('A3', [art('docs/project/launch.md'), art('docs/team/ownership.md')], None),
    ('A3', [art('README.md','uninspected','UNKNOWN'), art('docs/team/roles.md','scaffold','BASELINE')], None),
])
def test_mixed_repo_foundations(gate, repo, expected):
    concern = foundation_concern(gate, [a.to_dict() for a in repo])
    assert (concern.id.split('-')[1] if concern else None) == expected
    if concern:
        assert 'not proof' in concern.statement
        assert all(ref.startswith('PATH:') for ref in concern.evidence_refs)


def test_frozen_a3_snapshot_can_prioritize_a1_without_grade():
    repo = [art('README.md','scaffold','BASELINE'), art('docs/team/roles.md','scaffold','BASELINE'),
            art('docs/architecture/architecture.md','scaffold','BASELINE')]
    evidence = build_snapshot('A3', 'team/repo', 'frozen', [x.path for x in repo], artifacts=repo)
    assert evidence.challenge_candidates[0]['id'] == 'foundation-A1-for-A3'
    challenge = ChallengeEngine(ai=object()).start('A3', evidence)
    assert 'A1' in challenge.prompt and 'A3' in challenge.prompt
    assert 'grade' not in challenge.prompt.lower()


class DialogueProbe:
    def __init__(self):
        self.systems = []

    def available(self):
        return True

    def reviewer_turn(self, system, user):
        self.systems.append(system)
        # Deliberately request a later-stage link to verify server filtering.
        return {'student_intent': 'reasoning', 'understood_points': [],
                'reasoning_updates': blank_reasoning(), 'response_mode': 'teach',
                'stuck': False, 'frustrated': False, 'needs_direct_teaching': False,
                'reply': 'First check the cited team evidence; if it is scaffold, agree a real launch decision and owner.',
                'guidance_ids': ['ETIS-ES104-CONTEXT', 'ETIS-ES101-CONTEXT'],
                'teach_back': True, 'next_target': 'boundary_visible'}


@pytest.mark.parametrize('gate,student,expected', [
    ('A3', 'Our A1 launch is late. What is the first risk?', 'A1'),
    ('A5', 'We are actually at A3. How do boundaries affect the slice?', 'A3'),
    ('A5', 'I am stuck on A4 tests. Show me how.', 'A4'),
    ('A3', 'I disagree with the A2 estimate finding; our record changed.', 'A2'),
    ('A3', 'What does the current A3 snapshot actually prove?', 'A3'),
    ('A3', 'What are the largest risks for our project launch gate?', 'A1'),
])
def test_weak_average_strong_student_topics_and_guidance(gate, student, expected):
    probe = DialogueProbe()
    challenge = ChallengeEngine(ai=probe).start(gate, build_snapshot(gate, 'team/repo', 'sha', []))
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, student, blank_reasoning(), conversation_memory={},
        evidence_context='The current frozen snapshot includes only inspected excerpts.')
    assert reply['coaching_phase'] == expected
    assert f'question is about {expected}' in probe.systems[0]
    assert all(expected in ref['phase_ids'] for ref in reply['guidance_refs'])
    if expected == 'A1':
        assert any(ref['stage'] == 'ES-101' for ref in reply['guidance_refs'])
        assert all(ref['stage'] != 'ES-104' for ref in reply['guidance_refs'])


def test_followup_and_future_phase_are_bounded():
    assert coaching_phase('A5', 'What should we do next?', 'A3') == 'A3'
    assert coaching_phase('A3', 'How about A5?', 'A1') == 'A3'
    assert coaching_phase('A5', 'Now discuss A4 evidence', 'A3') == 'A4'
    assert coaching_phase('A3', 'Does our architecture support the slice?', 'A1') == 'A3'


def test_a1_pronoun_followup_uses_previous_answer_and_repairs_a3_pivot():
    class Probe(DialogueProbe):
        def reviewer_turn(self, system, user):
            self.systems.append(system)
            self.users = getattr(self, 'users', []) + [user]
            reply = ('For the A3 control, show a PR and an architecture review.'
                     if len(self.systems) == 1 else
                     'For the A1 launch decision, record a named decision owner and a real issue '
                     'that shows who decided and how disagreement was resolved.')
            return {'student_intent': 'reasoning', 'understood_points': [],
                    'reasoning_updates': blank_reasoning(), 'response_mode': 'conversation',
                    'stuck': False, 'frustrated': False, 'needs_direct_teaching': False,
                    'reply': reply, 'guidance_ids': ['ETIS-ES100-PRINCIPLES'],
                    'teach_back': False, 'next_target': 'ownership_visible'}

    probe = Probe()
    challenge = ChallengeEngine(ai=probe).start('A3', build_snapshot('A3', 'team/repo', 'sha', []))
    previous = 'For A1, decide who owns launch decisions and records disagreement.'
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, 'What would good evidence of that look like?', blank_reasoning(),
        conversation_memory={'coaching_phase': 'A1'},
        conversation_history=[{'actor': 'student', 'content': 'We are still at A1.'},
                              {'actor': 'reviewer', 'content': previous}],
        evidence_context='One commit, no issues or PRs in frozen snapshot.',
    )
    assert reply['coaching_phase'] == 'A1'
    assert 'A1 launch decision' in reply['text']
    assert previous in probe.users[0]
    assert 'not the question being asked' in probe.users[0]
    assert 'Original board finding:' not in probe.users[0]
    assert len(probe.systems) == 2
    assert all('A1' in ref['phase_ids'] for ref in reply['guidance_refs'])


def test_production_a1_followup_does_not_receive_a3_finding_or_excerpts():
    class Probe(DialogueProbe):
        def reviewer_turn(self, system, user):
            self.user = user
            self.systems.append(system)
            return {'student_intent': 'reasoning', 'understood_points': [],
                    'reasoning_updates': blank_reasoning(), 'response_mode': 'conversation',
                    'stuck': False, 'frustrated': False, 'needs_direct_teaching': False,
                    'reply': ('For A1, a team-reviewed launch record should name the problem, '
                              'stakeholder, success measure, and owner.'),
                    'guidance_ids': ['ETIS-ES101-CONTEXT'], 'teach_back': False}

    probe = Probe()
    challenge = ChallengeEngine(ai=probe).start('A3', build_snapshot('A3', 'team/repo', 'sha', []))
    challenge.prompt = 'A3 architecture assumptions are unverified.'
    prior = ('The largest A1 risk is launching without a shared problem, scope, '
             'stakeholders, and success criteria. Write a short engineering-context statement.')
    package = {'phase_id': 'A3', 'commit_sha': 'sha',
               'challenge': {'prompt': challenge.prompt},
               'relevant_artifacts': [{'path': 'docs/architecture/architecture.md',
                                      'content_excerpt': 'A3 scale and failure assumptions'}],
               'github_signals': {'issue_count': 0}}
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, 'What would good evidence of that look like?”', blank_reasoning(),
        conversation_memory={'coaching_phase': 'A1'},
        conversation_history=[{'actor': 'reviewer', 'content': challenge.prompt},
                              {'actor': 'student', 'content': 'We are still working on our A1 launch.'},
                              {'actor': 'reviewer', 'content': prior}],
        evidence_context=__import__('json').dumps(package),
    )
    assert reply['coaching_phase'] == 'A1'
    assert 'team-reviewed launch record' in reply['text']
    assert prior in probe.user
    assert challenge.prompt not in probe.user
    assert 'A3 scale and failure assumptions' not in probe.user
    assert 'issue_count' in probe.user


def test_overt_a3_concern_pivot_is_caught_but_dependency_is_allowed():
    assert earlier_topic_drift('For the A3 concern, make an assumption table.', 'A1', 'A3')
    assert earlier_topic_drift('If you meant the separate A1 question, say so.', 'A1', 'A3')
    assert not earlier_topic_drift('For A1, agree the scope; that also reduces A3 risk.', 'A1', 'A3')


def test_repeated_model_drift_produces_bounded_a1_help():
    class DriftingProbe(DialogueProbe):
        def reviewer_turn(self, system, user):
            self.systems.append(system)
            return {'student_intent': 'reasoning', 'understood_points': [],
                    'reasoning_updates': blank_reasoning(), 'response_mode': 'conversation',
                    'stuck': False, 'frustrated': False, 'needs_direct_teaching': False,
                    'reply': 'For the A3 concern, write an architecture assumptions table.',
                    'guidance_ids': [], 'teach_back': False}

    probe = DriftingProbe()
    challenge = ChallengeEngine(ai=probe).start('A3', build_snapshot('A3', 'team/repo', 'sha', []))
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, 'What would good evidence of that look like?', blank_reasoning(),
        conversation_memory={'coaching_phase': 'A1'},
        conversation_history=[{'actor': 'student', 'content': 'Our A1 launch is incomplete.'},
                              {'actor': 'reviewer', 'content': 'Agree on the A1 problem and success measure.'}],
        evidence_context='A3 architecture excerpt',
    )
    assert len(probe.systems) == 2
    assert 'For your A1 launch question' in reply['text']
    assert 'illustrative' in reply['text']
    assert 'architecture assumptions table' not in reply['text']


def test_explicit_selected_evidence_changes_topic_from_prior_a1():
    probe = DialogueProbe()
    challenge = ChallengeEngine(ai=probe).start('A3', build_snapshot('A3', 'team/repo', 'sha', []))
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, 'What does this show?', blank_reasoning(),
        conversation_memory={'coaching_phase': 'A1'},
        evidence_refs=['PATH:docs/architecture/architecture.md'],
        evidence_context='Selected frozen architecture artifact.',
    )
    assert reply['coaching_phase'] == 'A3'
    prior, _, _ = ChallengeEngine(ai=probe).converse(
        challenge, 'How do these roles support our launch?', blank_reasoning(),
        conversation_memory={'coaching_phase': 'A1'},
        evidence_refs=['PATH:docs/team/roles.md'],
        evidence_context='Selected frozen team roles artifact.',
    )
    assert prior['coaching_phase'] == 'A1'
