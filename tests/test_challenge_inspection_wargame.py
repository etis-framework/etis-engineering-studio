"""Adversarial A1-A6 challenge-inspection matrix for repository and student maturity."""

import pytest

from apps.api.app.services.challenge_engine import ChallengeEngine, blank_reasoning
from apps.api.app.services.evidence import build_snapshot
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.repository_intelligence import ArtifactFact


PHASE = {
    'A1': ('docs/launch/record.md', 'Stakeholder scope success measure decision owner review outcome.'),
    'A2': ('docs/planning/work-plan.md', 'Estimate dependency owner re-estimation trigger review outcome.'),
    'A3': ('docs/architecture/architecture.md', 'Component responsibility interface boundary tradeoff review outcome.'),
    'A4': ('docs/build/integration-record.md', 'Implementation review integration manual check observed result.'),
    'A5': ('docs/release/acceptance.md', 'Acceptance result defect residual risk release decision.'),
    'A6': ('docs/operations/runbook.md', 'Monitoring recovery restore drill owner observed result.'),
}


class MatrixProbe:
    def __init__(self, maturity, student):
        self.maturity = maturity
        self.student = student
        self.critic_user = ''

    def available(self):
        return True

    def reviewer_turn(self, system, user):
        return {
            'student_intent': 'evidence_dispute',
            'understood_points': [],
            'reasoning_updates': blank_reasoning(),
            'stuck': self.student == 'weak',
            'frustrated': False,
            'needs_direct_teaching': False,
            'response_mode': 'challenge',
            'next_target': 'evidence_boundary_visible',
            # Deliberately poor first draft; the independent critic must repair it.
            'reply': 'I found the file. Which passage changes the board interpretation?',
            'guidance_ids': [],
            'handoff_lens': None,
            'teach_back': False,
        }

    def critique_reviewer_turn(self, system, user):
        self.critic_user = user
        if self.maturity == 'weak':
            revised = (
                'I inspected the selected frozen source. It is still starter/scaffold material, '
                'so its presence does not demonstrate the disputed practice. You can use the '
                'scaffold to start, but record one genuine team decision or result before claiming it as evidence.'
            )
        elif self.maturity == 'average':
            revised = (
                'I inspected the selected frozen source. It supports part of the claim, but the '
                'operating result is incomplete. You have enough structure to continue the work; '
                'the stronger completion claim should remain open until the missing result is recorded.'
            )
        else:
            revised = (
                'I inspected the selected frozen source. It records the disputed practice and its '
                'observed result, so the review interpretation should be narrowed or corrected. '
                'The next question is whether that demonstrated practice is sufficient for the engineering risk.'
            )
        return {'acceptable': False, 'issues': ['challenge inspection'], 'revised_reply': revised}


@pytest.mark.parametrize('phase', list(PHASE))
@pytest.mark.parametrize('maturity', ['weak', 'average', 'strong'])
@pytest.mark.parametrize('student', ['weak', 'average', 'strong'])
def test_a1_a6_repository_and_student_matrix(phase, maturity, student):
    path, strong_content = PHASE[phase]
    content = {
        'weak': 'Starter template. TODO: replace this text with team evidence.',
        'average': strong_content.split(' review outcome')[0] + '. Review outcome still TODO.',
        'strong': strong_content,
    }[maturity]
    artifact = ArtifactFact(
        path=path,
        exists=True,
        provenance={'weak': 'BASELINE', 'average': 'TEAM_ADAPTED', 'strong': 'TEAM_ADDED'}[maturity],
        quality={'weak': 'scaffold', 'average': 'partial', 'strong': 'reviewable'}[maturity],
        content_excerpt=content,
        review_content=content,
    )
    evidence = build_snapshot(phase, 'synthetic/team', 'frozen-sha', [path], artifacts=[artifact])
    challenge = ChallengeEngine(ai=object()).start(phase, evidence)
    package = EvidencePackageBuilder().build_for_turn(
        evidence.to_dict(), challenge.to_dict(), [f'PATH:{path}']
    ).to_prompt_text()

    student_text = {
        'weak': 'we did this already',
        'average': 'We are not this far yet; do we have enough evidence to start?',
        'strong': 'This exact frozen source records the decision and result; please reconsider the finding.',
    }[student]
    probe = MatrixProbe(maturity, student)
    reply, _, _ = ChallengeEngine(ai=probe).converse(
        challenge,
        student_text,
        blank_reasoning(),
        intent='evidence_dispute',
        evidence_refs=[f'PATH:{path}', f'FINDING:{challenge.id}'],
        evidence_context=package,
        conversation_memory={},
        student_name='Synthetic Student',
    )

    text = reply['text']
    assert 'Which passage' not in text
    assert path in probe.critic_user
    assert 'selected_paths=' in probe.critic_user
    assert 'grade' not in text.lower()
    if maturity == 'weak':
        assert 'does not demonstrate' in text
    elif maturity == 'average':
        assert 'supports part' in text and 'remain open' in text
    else:
        assert 'narrowed or corrected' in text
