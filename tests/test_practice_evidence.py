"""A control's operating record must be visible before the Studio praises use."""

from apps.api.app.services.artifact_condition import condition_for
from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor


PATH = 'docs/ai/ai-use-log.md'
ENTRY = ('AI assistant suggested dropping the offline acceptance criterion; '
         'Maya compared it with REQ-04 and rejected the suggestion on 2026-09-22.')
PREFIX = ('The team records material AI assistance and human verification below.\n' +
          'Team AI policy and context.\n' * 65)


class FakeAI:
    def __init__(self, candidate):
        self.candidate = candidate

    def available(self):
        return True

    def repository_assessment(self, system, user):
        self.user = user
        return {'strengths': [], 'findings': [], 'equivalent_evidence': [],
                'claim_support': [self.candidate]}


def candidate(**overrides):
    return {
        'expected_path': PATH, 'support_path': PATH, 'support_quote': ENTRY,
        'operating_evidence_path': PATH, 'operating_evidence_quote': ENTRY,
        'support_kind': 'demonstrated', 'judgment': 'strong', 'confidence': 'high',
        'rationale': 'One material AI suggestion was recorded and checked against REQ-04.',
        'limitation': 'The excerpt does not establish that every use was recorded.',
        'next_step': 'Check other planning work for material AI influence.',
        **overrides,
    }


def artifact(content=None, **overrides):
    return {'path': PATH, 'provenance': 'TEAM_ADAPTED', 'quality': 'reviewable',
            'summary': '', 'size': 2400, 'content_excerpt': content or PREFIX + ENTRY,
            **overrides}


def assess(c, artifacts=None):
    ai = FakeAI(c)
    result = SemanticEvidenceAssessor(ai).assess(
        'A2', 'team/repo', 'frozen', artifacts or [artifact()], {})
    return result.claim_support, ai.user


def test_filled_ai_log_entry_near_end_is_bounded_operating_support():
    supports, context = assess(candidate())
    assert ENTRY in context and len(supports) == 1
    assert supports[0]['operating_evidence_path'] == PATH
    state = condition_for({'title': PATH, 'status': 'present', 'quality': 'reviewable'}, [], supports)
    assert state['key'] == 'strong'
    assert state['support']['operating_evidence_quote'] == ENTRY
    assert 'operating record' in state['why']


def test_policy_only_blank_log_or_explicit_no_use_is_not_fabricated_use():
    policy = 'Every material AI suggestion is logged with a human verification decision.'
    for text in (policy, 'No AI assistance was used during the reviewed period.'):
        supports, _ = assess(candidate(support_quote=text, operating_evidence_quote=''),
                             [artifact(content=text)])
        assert supports == []
    supports, _ = assess(candidate(support_kind='defined'), [artifact(content=ENTRY)])
    assert supports == []
    example = 'Example: AI suggested a scope cut and Maya reviewed it against REQ-04.'
    assert assess(candidate(support_quote=example, operating_evidence_quote=example),
                  [artifact(content=example)])[0] == []


def test_operating_record_must_be_exact_team_authored_inspectable_and_disclosed():
    assert assess(candidate(operating_evidence_quote='Invented team verification.' ))[0] == []
    assert assess(candidate(operating_evidence_path='docs/ai/invented.md'))[0] == []
    assert assess(candidate(), [artifact(provenance='BASELINE')])[0] == []
    assert assess(candidate(), [artifact(quality='uninspected')])[0] == []
    assert assess(candidate(), [artifact(content=PREFIX + ENTRY + ' sk-' + 'x' * 24)])[0] == []
    assert assess(candidate(), [artifact(content=PREFIX)])[0] == []


def test_equivalent_operating_record_stays_cautious():
    alternate = 'docs/decisions/ai-review-record.md'
    supports, _ = assess(candidate(support_path=alternate, operating_evidence_path=alternate),
                         [artifact(path=alternate, content_excerpt=ENTRY, size=500)])
    assert len(supports) == 1
    item = {'title': PATH, 'status': 'equivalent', 'equivalent_path': alternate,
            'quality': 'reviewable'}
    state = condition_for(item, [], supports)
    assert state['key'] == 'okay'
    assert state['support']['operating_evidence_path'] == alternate


def test_conflict_blocks_positive_card_and_defined_plans_remain_bounded():
    supports, _ = assess(candidate())
    item = {'title': PATH, 'status': 'present', 'quality': 'reviewable'}
    concern = {'id': 'C', 'review_scope': 'course_readiness', 'severity': 4,
               'evidence_refs': ['PATH:' + PATH], 'lifecycle': {'status': 'evidence_disputed'}}
    assert condition_for(item, [concern], supports)['key'] == 'concern'
    defined = [{**supports[0], 'support_kind': 'defined', 'judgment': 'okay'}]
    state = condition_for(item, [], defined)
    assert state['key'] == 'okay'
    assert 'use is not established' in state['why']


def test_mixed_team_keeps_its_strength_without_clearing_other_course_concern():
    from apps.api.app.services.board_readiness import build_phase_preparation

    estimate = 'docs/planning/estimates.md'
    support = {'expected_path': estimate, 'support_path': estimate,
               'claim': 'Estimate range and assumptions are explicit.',
               'support_quote': 'Task T-1: 3–5 days, owner Maya, API access assumption.',
               'support_kind': 'demonstrated', 'judgment': 'strong', 'confidence': 'high',
               'provenance': 'REVIEW', 'inspection_scope': 'bounded_excerpt',
               'rationale': 'The team recorded a bounded estimate.',
               'limitation': 'The dependency needs checking.', 'next_step': 'Verify API access.'}
    concern = {'id': 'C', 'title': 'AI control has no operating record',
               'statement': 'The log is blank.', 'review_scope': 'course_readiness',
               'rank_score': 28, 'severity': 4, 'evidence_refs': ['PATH:' + PATH]}
    evidence = {'items': [
        {'title': estimate, 'status': 'present', 'quality': 'reviewable'},
        {'title': PATH, 'status': 'present', 'quality': 'reviewable'},
    ], 'findings': [concern], 'claim_support': [support]}
    preparation = build_phase_preparation('A2', evidence)
    assert preparation['focus']['title'] == concern['title']
    assert [x['path'] for x in preparation['supported']] == [estimate]
