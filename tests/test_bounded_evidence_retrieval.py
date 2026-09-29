"""Frozen bounded retrieval for long files and alternate docs locations."""

from apps.api.app.routers.reviews import _public_evidence_snapshot
from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import artifact_from_bytes


EXPECTED = 'docs/ai/ai-use-log.md'
ALTERNATE = 'docs/team/working-notes/assistant-decisions.md'
ENTRY = ('AI assistant proposed removing offline behavior. Maya compared it with REQ-04 '
         'and rejected that suggestion after a human review on 2026-09-22.')


class CandidateAI:
    def __init__(self, support=None, equivalent=None):
        self.support = support or []
        self.equivalent = equivalent or []
        self.prompt = ''

    def available(self):
        return True

    def repository_assessment(self, system, user):
        self.prompt = user
        return {'strengths': [], 'findings': [], 'claim_support': self.support,
                'equivalent_evidence': self.equivalent}


def support(path=ALTERNATE, quote=ENTRY):
    return {'expected_path': EXPECTED, 'support_path': path, 'support_quote': quote,
            'operating_evidence_path': path, 'operating_evidence_quote': quote,
            'support_kind': 'demonstrated', 'judgment': 'strong', 'confidence': 'high',
            'rationale': 'A material AI suggestion has a recorded human decision.',
            'limitation': 'Selected windows do not establish every use was logged.',
            'next_step': 'Check the full frozen source and other planning records.'}


def equivalent(path=ALTERNATE, quote=ENTRY):
    return {'expected_path': EXPECTED, 'actual_path': path, 'support_quote': quote,
            'explanation': 'A team operating record is in this other docs location.',
            'confidence': 'high'}


def fact(path, text):
    return artifact_from_bytes(path, text.encode()).to_dict()


def test_later_operating_record_and_alternate_nested_docs_are_bounded_and_citable():
    alternate = fact(ALTERNATE, 'A' * 14000 + '\n' + ENTRY + '\n' + 'B' * 14000)
    assert ENTRY not in alternate['content_excerpt']
    assert ENTRY not in alternate['review_content']
    assert any(ENTRY in w['text'] for w in alternate['analysis_windows'])
    ai = CandidateAI([support()], [equivalent()])
    result = SemanticEvidenceAssessor(ai).assess('A2', 'team/repo', 'frozen',
                                                  [fact(EXPECTED, 'Empty table. ' * 20), alternate], {})
    assert ENTRY in ai.prompt
    assert len(result.equivalent_evidence) == 1
    assert result.equivalent_evidence[0]['actual_path'] == ALTERNATE
    assert len(result.claim_support) == 1
    assert result.claim_support[0]['judgment'] == 'okay'  # long file was sampled
    assert result.inspection['scope'] == 'bounded_windows'
    public = _public_evidence_snapshot({'artifacts': [alternate]})['artifacts'][0]
    assert 'analysis_windows' not in public and 'review_content' not in public


def test_many_planning_files_cannot_hide_an_alternate_docs_record():
    artifacts = [fact(f'docs/planning/plan-{i:02d}.md', 'Estimate T-01 owner Ana. ' * 55)
                 for i in range(25)]
    artifacts += [fact(ALTERNATE, ENTRY)]
    ai = CandidateAI([support()], [equivalent()])
    result = SemanticEvidenceAssessor(ai).assess('A2', 'team/repo', 'frozen', artifacts, {})
    assert ALTERNATE in ai.prompt and len(result.equivalent_evidence) == 1
    assert result.inspection['omitted_artifact_count'] > 0
    assert result.inspection['inspected_artifact_count'] < len(artifacts)


def test_invented_truncated_sample_and_secret_tainted_support_are_rejected():
    actual = fact(ALTERNATE, 'A' * 14000 + '\n' + ENTRY + '\n' + 'B' * 14000)
    for wrong in ('An invented human verification entry appears here.',
                  'Example: AI assistant proposed a task. Maya reviewed it against REQ-04.'):
        ai = CandidateAI([support(quote=wrong)], [equivalent(quote=wrong)])
        result = SemanticEvidenceAssessor(ai).assess('A2', 'team/repo', 'frozen', [actual], {})
        assert not result.claim_support and not result.equivalent_evidence
    secret = 'sk-proj-' + 'A' * 40
    tainted = fact(ALTERNATE, 'A' * 14000 + '\n' + ENTRY + ' ' + secret + '\n' + 'B' * 14000)
    ai = CandidateAI([support()], [equivalent()])
    result = SemanticEvidenceAssessor(ai).assess('A2', 'team/repo', 'frozen', [tainted], {})
    assert secret not in ai.prompt
    assert not result.claim_support and not result.equivalent_evidence


def test_policy_or_attested_non_use_does_not_become_an_operating_record():
    for text in ('Every AI suggestion must be reviewed by a human before acceptance.',
                 'No AI assistance was used during this period.'):
        ai = CandidateAI([support(quote=text)], [equivalent(quote=text)])
        result = SemanticEvidenceAssessor(ai).assess('A2', 'team/repo', 'frozen',
                                                      [fact(ALTERNATE, text)], {})
        assert not result.claim_support
        assert not result.equivalent_evidence


def test_student_challenge_of_later_passage_uses_same_frozen_windows():
    record = fact(ALTERNATE, 'A' * 14000 + '\n' + ENTRY + '\n' + 'B' * 14000)
    evidence = {'phase_id': 'A2', 'repo_full_name': 'team/repo', 'commit_sha': 'frozen',
                'artifacts': [record], 'items': [], 'findings': [], 'repository_metrics': {}}
    package = EvidencePackageBuilder().build_for_turn(evidence, {}, ['PATH:' + ALTERNATE])
    assert ENTRY in package.to_prompt_text()
    assert package.commit_sha == 'frozen'
    assert 'Frozen excerpt, characters' in package.relevant_artifacts[0]['content_excerpt']
    initial = EvidencePackageBuilder().build(evidence, {'evidence_refs': ['PATH:' + ALTERNATE]})
    assert ENTRY in initial.to_prompt_text()
