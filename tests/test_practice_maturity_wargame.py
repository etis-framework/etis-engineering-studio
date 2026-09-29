"""Synthetic teams test how bounded claims survive optimistic model output."""

from pathlib import Path

import pytest

from apps.api.app.services.artifact_condition import condition_for, supported_observations
from apps.api.app.services.board_readiness import build_phase_preparation
from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor
from apps.api.app.services.repository_intelligence import artifact_from_bytes


REESTIMATE = 'docs/planning/re-estimation.md'
EVENT = ('After API access failed on 2026-09-22, Priya revised E-17 from 3–5 to '
         '5–7 days and linked the dependency to R-04.')
PLAN = ('If API access slips, Priya will revise E-17 within one day and update '
        'the dependent Cycle 1 schedule.')


class OptimisticAssessor:
    def __init__(self, claim):
        self.claim = claim

    def available(self):
        return True

    def repository_assessment(self, system, user):
        return {'strengths': ['This team is fully ready.'], 'findings': [],
                'equivalent_evidence': [], 'claim_support': [self.claim]}


def candidate(path=REESTIMATE, quote=EVENT, **changes):
    return {'expected_path': path, 'support_path': path, 'support_quote': quote,
            'operating_evidence_path': path, 'operating_evidence_quote': quote,
            'support_kind': 'demonstrated', 'judgment': 'strong', 'confidence': 'high',
            'rationale': 'The team recorded an actual change after a dependency slipped.',
            'limitation': 'One change does not prove every estimate is current.',
            'next_step': 'Check the schedule and dependent tasks against the revised estimate.',
            **changes}


def repo_artifacts(root: Path, files: dict[str, str]):
    artifacts = []
    for name, content in files.items():
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        artifact = artifact_from_bytes(name, file.read_bytes()).to_dict()
        # The synthetic repository supplies adapted, inspectable team material.
        artifact.update(provenance='TEAM_ADAPTED', quality='reviewable')
        artifacts.append(artifact)
    return artifacts


def assess(phase, path, text, claim, tmp_path):
    artifacts = repo_artifacts(tmp_path, {path: text})
    return SemanticEvidenceAssessor(OptimisticAssessor(claim)).assess(
        phase, 'team/synthetic', 'frozen-commit', artifacts, {}).claim_support


@pytest.mark.parametrize(('profile', 'text', 'claim', 'expected'), [
    ('weak scaffold', 'TODO: Record re-estimation once work begins.', candidate(), None),
    ('polished example', 'Example: ' + EVENT, candidate(quote='Example: ' + EVENT,
                                                  operating_evidence_quote='Example: ' + EVENT), None),
    ('quote extracted from an illustrative row', 'Example: ' + EVENT, candidate(), None),
    ('average defined trigger', PLAN, candidate(quote=PLAN, support_kind='defined',
                                                operating_evidence_path='', operating_evidence_quote=''), 'okay'),
    ('strong recorded change', EVENT, candidate(), 'strong'),
    ('strong sample of actual work',
     'After checking a sample of five blocked tasks on 2026-09-22, Priya revised E-17 from 3–5 to 5–7 days.',
     candidate(quote='After checking a sample of five blocked tasks on 2026-09-22, Priya revised E-17 from 3–5 to 5–7 days.',
               operating_evidence_quote='After checking a sample of five blocked tasks on 2026-09-22, Priya revised E-17 from 3–5 to 5–7 days.'), 'strong'),
    ('unsupported strong assertion', PLAN, candidate(quote=PLAN,
                       operating_evidence_path='', operating_evidence_quote=''), None),
    ('invented operating record', PLAN, candidate(quote=PLAN,
                                                operating_evidence_quote=EVENT), None),
])
def test_a2_reestimation_practice_maturity(profile, text, claim, expected, tmp_path):
    result = assess('A2', REESTIMATE, text, claim, tmp_path)
    assert (result[0]['judgment'] if result else None) == expected, profile
    if result:
        item = {'title': REESTIMATE, 'status': 'present', 'quality': 'reviewable'}
        assert condition_for(item, [], result)['key'] == expected


@pytest.mark.parametrize(('phase', 'path', 'definition', 'event'), [
    ('A3', 'docs/reviews/architecture-review.md',
     'The review protocol will assign an owner and disposition to each architecture concern.',
     'On 2026-09-22, Maya reviewed AR-04, accepted the boundary correction, and closed the finding.'),
    ('A4', '.github/workflows/ci.yml',
     'The workflow should run pytest on pull requests and report failures before merge.',
     'CI run 17 failed on 2026-09-22, Priya corrected test T-4, and run 18 passed before merge.'),
    ('A5', 'docs/testing/verification.md',
     'The release plan will verify the approval path before presentation.',
     'On 2026-09-22, test T-4 failed the unauthorized approval path; Maya corrected the rule and reran it successfully.'),
    ('A6', 'docs/operations/recovery.md',
     'The runbook should test restoration and assign an operator.',
     'On 2026-09-22, Priya restored the backup in staging and verified the ticket count against the source.'),
])
def test_practice_claims_need_actual_record_for_demonstrated_support(
    phase, path, definition, event, tmp_path,
):
    expected_path = path if phase in {'A3', 'A4'} else path.rsplit('/', 1)[0] + '/'
    optimistic = candidate(path=path, quote=definition,
                           expected_path=expected_path,
                           operating_evidence_path='', operating_evidence_quote='')
    assert assess(phase, path, definition, optimistic, tmp_path) == []
    defined = candidate(path=path, expected_path=expected_path, quote=definition, support_kind='defined',
                        operating_evidence_path='', operating_evidence_quote='')
    bounded = assess(phase, path, definition, defined, tmp_path)
    assert bounded and bounded[0]['judgment'] == 'okay'
    demonstrated = candidate(path=path, expected_path=expected_path, quote=event)
    operated = assess(phase, path, event, demonstrated, tmp_path)
    assert operated and operated[0]['judgment'] == 'strong'


@pytest.mark.parametrize('student', ['confused', 'average', 'strong'])
@pytest.mark.parametrize('repository', ['weak', 'average', 'strong'])
def test_nine_repository_student_openings_remain_bounded(repository, student, tmp_path):
    from types import SimpleNamespace
    from apps.api.app.services.challenge_engine import ChallengeEngine, blank_reasoning

    if repository == 'strong':
        text, claim = EVENT, candidate()
    elif repository == 'average':
        text, claim = PLAN, candidate(quote=PLAN, support_kind='defined',
                                     operating_evidence_path='', operating_evidence_quote='')
    else:
        text, claim = 'TODO: fill in the re-estimation record.', candidate()
    supports = assess('A2', REESTIMATE, text, claim, tmp_path)
    item = {'title': REESTIMATE, 'status': 'present' if repository != 'weak' else 'scaffold',
            'quality': 'reviewable' if repository != 'weak' else 'thin'}
    evidence = SimpleNamespace(items=[SimpleNamespace(**item)], findings=[],
                               challenge_candidates=[], claim_support=supports,
                               strengths=['The plan is perfect.'], repository_metrics={})
    opening = ChallengeEngine(ai=object()).start('A2', evidence).prompt
    expected = supported_observations(evidence)
    assert all(observation in opening for observation in expected)
    assert ('Strong support' in opening) == (repository == 'strong')
    assert ('Okay support' in opening) == (repository == 'average')
    assert 'The plan is perfect.' not in opening
    assert not any(word in opening.lower() for word in ('predicted grade', 'full points'))

    # The same repository cannot turn a student's fluency into evidence. The
    # coaching prompt must have a route for each student without changing facts.
    coaching = {'confused': 'I do not understand re-estimation. Explain and show me how.',
                'average': 'Our trigger is API access slipping; what should we check?',
                'strong': 'I challenge the claim: the record shows a revised estimate.'}[student]
    preparation = build_phase_preparation('A2', {'items': [item], 'findings': [],
                                                  'claim_support': supports})
    assert len(preparation['supported']) == (0 if repository == 'weak' else 1)
    assert 'grade' in preparation['boundary']

    class DialogueProbe:
        def available(self):
            return True

        def reviewer_turn(self, system, user):
            self.system, self.user = system, user
            teaching = student == 'confused'
            return {'student_intent': 'stuck' if teaching else 'reasoning',
                    'understood_points': [], 'reasoning_updates': blank_reasoning(),
                    'stuck': teaching, 'frustrated': False,
                    'needs_direct_teaching': teaching,
                    'next_target': 'evidence_boundary_visible',
                    'reply': ('Here is a bounded example: revise an estimate when its '
                              'dependency changes, and link the affected schedule. '
                              'Apply that pattern to your team record.' if teaching else
                              'Let us test the cited record and its limits before changing the plan.'),
                    'guidance_ids': [], 'handoff_lens': None, 'teach_back': teaching}

    probe = DialogueProbe()
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        ChallengeEngine(ai=probe).start('A2', evidence), coaching,
        blank_reasoning(), conversation_memory={}, student_name='Alex Rivera',
        evidence_context='\n'.join(expected) or 'No positive claim established in this snapshot.',
    )
    assert coaching in probe.user
    assert all(observation in probe.user for observation in expected)
    assert 'Teach the concept directly' in probe.system
    assert 'grade' not in reply['text'].lower()
    if student == 'confused':
        assert reply['kind'] == 'teaching'
