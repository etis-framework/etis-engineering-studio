"""Synthetic weak/average/strong repositories and student evidence questions."""

from apps.api.app.services.artifact_condition import condition_for
from apps.api.app.services.evidence import apply_equivalent_support, build_snapshot
from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact, _find_artifact, artifact_from_bytes

EXPECTED = 'docs/planning/estimates.md'
ALTERNATE = 'docs/team/delivery-estimates.md'
OTHER = 'docs/decisions/cycle1-capacity.md'
QUOTE = 'E-17 ranges from 3 to 5 days, owned by Priya, assuming API access is available.'
SECOND = 'Priya compared the Cycle 1 capacity with E-17 and approved the 3 to 5 day range.'


class CandidateAI:
    def __init__(self, supports, equivalents):
        self.supports, self.equivalents = supports, equivalents

    def available(self):
        return True

    def repository_assessment(self, system, user):
        return {'strengths': [], 'findings': [], 'claim_support': self.supports,
                'equivalent_evidence': self.equivalents}


def artifact(path, text):
    return artifact_from_bytes(path, (text + '\nThis record documents the team decision for Cycle 1 and its bounded planning assumptions.').encode()).to_dict()


def candidate(*, judgment='strong', kind='demonstrated', second=True):
    return {'expected_path': EXPECTED, 'support_path': ALTERNATE, 'support_quote': QUOTE,
            'corroborating_evidence': [{'path': OTHER, 'quote': SECOND}] if second else [],
            'operating_evidence_path': '', 'operating_evidence_quote': '',
            'support_kind': kind, 'judgment': judgment, 'confidence': 'high',
            'rationale': 'An owned estimate and capacity decision agree for E-17.',
            'limitation': 'Only the cited estimate and decision are visible here.',
            'next_step': 'Verify the API access assumption and revise the estimate if it changes.'}


def equivalent(path=ALTERNATE, quote=QUOTE):
    return {'expected_path': EXPECTED, 'actual_path': path, 'support_quote': quote,
            'explanation': 'The team estimate is in a different docs location.', 'confidence': 'high'}


def assess(supports, equivalents, facts):
    return SemanticEvidenceAssessor(CandidateAI(supports, equivalents)).assess(
        'A2', 'team/repo', 'frozen', facts, {})


def snapshot(facts):
    return build_snapshot('A2', 'team/repo', 'frozen', [a['path'] for a in facts],
                          artifacts=[ArtifactFact(**a) for a in facts])


def estimate_item(result):
    return next(x for x in result.items if x.title == EXPECTED)


def test_weak_repository_suggestion_does_not_clear_gap_or_increase_coverage():
    weak = artifact(ALTERNATE, 'A polished estimate template with headings and no filled rows. ' * 3)
    result = snapshot([weak]); before = result.coverage
    result.equivalent_evidence = [equivalent()]
    apply_equivalent_support(result)
    assert estimate_item(result).status == 'missing'
    assert result.coverage == before
    assert any(f['category'] == 'missing_evidence' and f'PATH:{EXPECTED}' in f['evidence_refs']
               for f in result.findings)
    assert condition_for(vars(estimate_item(result)), [], [])['key'] == 'gap'


def test_average_alternate_and_strong_cross_file_record_are_claim_specific():
    facts = [artifact(ALTERNATE, QUOTE), artifact(OTHER, SECOND)]
    average = assess([candidate(judgment='okay', kind='defined', second=False)], [equivalent()], facts)
    result = snapshot(facts); result.claim_support = average.claim_support
    result.equivalent_evidence = average.equivalent_evidence
    apply_equivalent_support(result)
    item = estimate_item(result)
    assert item.status == 'equivalent' and item.equivalent_path == ALTERNATE
    assert condition_for(vars(item), result.findings, result.claim_support)['key'] == 'okay'

    strong = assess([candidate()], [equivalent()], facts)
    assert strong.claim_support[0]['corroborating_evidence'] == [{'path': OTHER, 'quote': SECOND}]
    result.claim_support = strong.claim_support
    assert condition_for(vars(item), result.findings, result.claim_support)['key'] == 'strong'
    assert all(f'PATH:{EXPECTED}' not in f.get('evidence_refs', [])
               for f in result.findings if f['category'] == 'missing_evidence')
    # A course concern on either supplied source blocks praise even if a different file is polished.
    finding = {'id': 'conflict', 'review_scope': 'course_readiness',
               'evidence_refs': [f'PATH:{OTHER}']}
    assert condition_for(vars(item), [finding], result.claim_support)['key'] == 'concern'


def test_wrong_claim_missing_or_invented_corroboration_cannot_promote():
    facts = [artifact(ALTERNATE, QUOTE), artifact(OTHER, SECOND)]
    bad = candidate(); bad['corroborating_evidence'][0]['quote'] = 'Invented approval from another team.'
    assert not assess([bad], [equivalent()], facts).claim_support
    bad = candidate(); bad['corroborating_evidence'][0]['path'] = 'docs/private/outside.md'
    assert not assess([bad], [equivalent()], facts).claim_support
    valid = assess([candidate()], [equivalent(path=OTHER, quote=SECOND)], facts)
    result = snapshot(facts); result.claim_support = valid.claim_support
    result.equivalent_evidence = valid.equivalent_evidence
    apply_equivalent_support(result)
    assert estimate_item(result).equivalent_path == OTHER  # linked corroboration is legitimate
    # A suggestion naming a different, unrelated source never becomes a confirmed location.
    result = snapshot(facts); result.claim_support = valid.claim_support
    result.equivalent_evidence = [equivalent(path='docs/irrelevant.md')]
    apply_equivalent_support(result)
    assert estimate_item(result).status == 'missing'


def test_mixed_directory_stays_partial_even_with_one_reviewable_child():
    good = ArtifactFact(path='docs/requirements/requirements.md', exists=True, provenance='TEAM_ADAPTED', quality='reviewable')
    blank = ArtifactFact(path='docs/requirements/starter.md', exists=True, provenance='BASELINE', quality='scaffold')
    rolled = _find_artifact([good, blank], 'docs/requirements/')
    result = build_snapshot('A2', 'team/repo', 'frozen', [good.path, blank.path], artifacts=[good, blank])
    item = next(x for x in result.items if x.title == 'docs/requirements/')
    assert rolled.quality == 'partial' and item.status == 'weak' and item.quality == 'partial'
    assert condition_for(vars(item), [], [])['label'] == 'Mixed evidence'


def test_student_dialogue_selection_uses_frozen_multi_file_record():
    facts = [artifact(ALTERNATE, QUOTE), artifact(OTHER, SECOND)]
    support = assess([candidate()], [equivalent()], facts).claim_support
    evidence = {'phase_id': 'A2', 'repo_full_name': 'team/repo', 'commit_sha': 'frozen',
                'items': [], 'artifacts': facts, 'claim_support': support, 'repository_metrics': {}}
    builder = EvidencePackageBuilder()
    for student in ('confused: where is the estimate?',
                    'average: explain how the range and capacity relate',
                    'strong: challenge whether E-17 assumed API access'):
        package = builder.build_for_turn(evidence, {'title': student}, ['PATH:' + EXPECTED])
        prompt = package.to_prompt_text()
        assert package.commit_sha == 'frozen'
        assert QUOTE in prompt and SECOND in prompt
        assert 'docs/irrelevant.md' not in prompt


def test_nine_repository_student_dialogue_contexts_keep_evidence_boundaries():
    student_questions = {
        'weak': 'I am stuck; what should we write first?',
        'average': 'Is this acceptable? Show me what to improve.',
        'strong': 'I disagree; show me the precise assumption and source.',
    }
    for repo in ('weak', 'average', 'strong'):
        facts = [] if repo == 'weak' else [artifact(ALTERNATE, QUOTE)]
        if repo == 'strong':
            facts.append(artifact(OTHER, SECOND))
        supports = [] if repo == 'weak' else assess(
            [candidate(judgment='okay', kind='defined', second=False) if repo == 'average'
             else candidate()], [equivalent()], facts).claim_support
        evidence = {'phase_id': 'A2', 'repo_full_name': 'team/repo', 'commit_sha': 'frozen',
                    'items': [], 'artifacts': facts, 'claim_support': supports,
                    'repository_metrics': {}}
        for student, question in student_questions.items():
            package = EvidencePackageBuilder().build_for_turn(
                evidence, {'title': question}, ['PATH:' + EXPECTED])
            text = package.to_prompt_text()
            assert package.commit_sha == 'frozen' and question in text
            assert 'Absence in the snapshot is not proof of absence everywhere' in text
            assert (QUOTE in text) == (repo != 'weak')
            assert (SECOND in text) == (repo == 'strong')
