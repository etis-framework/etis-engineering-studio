"""Positive claim support is bounded to frozen, team-authored excerpts."""

from apps.api.app.services.artifact_condition import condition_for, decorate_conditions, supported_observations
from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor


PATH = 'docs/planning/estimates.md'
QUOTE = 'E-17 has a range of 3 to 5 days, owned by Priya, with API access as its explicit assumption.'


class FakeAI:
    def __init__(self, support):
        self.support = support

    def available(self):
        return True

    def repository_assessment(self, system_prompt, user_prompt):
        return {'strengths': [], 'findings': [], 'equivalent_evidence': [],
                'claim_support': self.support}


def candidate(**overrides):
    value = {'expected_path': PATH, 'support_path': PATH, 'support_quote': QUOTE,
             'support_kind': 'demonstrated', 'judgment': 'strong', 'confidence': 'high',
             'rationale': 'A real team estimate names a range, owner, and assumption.',
             'limitation': 'The API dependency still needs verification.',
             'next_step': 'Confirm API access and update the range if it changes.'}
    return {**value, **overrides}


def artifact(**overrides):
    return {'path': PATH, 'provenance': 'TEAM_ADAPTED', 'quality': 'reviewable',
            'summary': '', 'size': 500, 'content_excerpt': QUOTE, **overrides}


def assess(support, artifacts=None):
    return SemanticEvidenceAssessor(FakeAI(support)).assess(
        'A2', 'team/repo', 'frozen-sha', artifacts or [artifact()], {})


def item(**overrides):
    return {'title': PATH, 'status': 'present', 'quality': 'reviewable',
            'source_provenance': 'TEAM_ADAPTED', **overrides}


def test_strong_claim_is_specific_quoted_and_challengeable():
    support = assess([candidate()]).claim_support
    assert len(support) == 1
    assert support[0]['claim'].startswith('Estimates use ranges')
    assert support[0]['provenance'] == 'REVIEW'
    condition = condition_for(item(), [], support)
    assert condition['label'] == 'Strong support'
    assert condition['support']['support_quote'] == QUOTE
    finding = {'id': 'F', 'review_scope': 'course_readiness', 'severity': 4,
               'evidence_refs': ['PATH:' + PATH], 'lifecycle': {'status': 'open'}}
    assert condition_for(item(), [finding], support)['label'] == 'Review concern'
    assert condition_for(item(), [{**finding, 'lifecycle': {'status': 'corrected'}}], support)['key'] == 'strong'


def test_average_defined_claim_is_okay_and_not_artifact_approval():
    support = assess([candidate(support_kind='defined', judgment='strong')]).claim_support
    assert support[0]['judgment'] == 'okay'
    condition = condition_for(item(), [], support)
    assert condition['label'] == 'Okay support'
    assert 'Limitation:' in condition['why']
    assert condition['support']['inspection_scope'] == 'bounded_excerpt'
    policy = 'Every estimate should name a range, owner, assumptions, and a verification trigger.'
    polished = assess([candidate(support_quote=policy)], [artifact(content_excerpt=policy)])
    assert not polished.claim_support


def test_weak_missing_scaffold_and_uninspected_still_take_precedence():
    support = assess([candidate()]).claim_support
    assert condition_for(item(status='missing'), [], support)['key'] == 'gap'
    assert condition_for(item(status='scaffold', source_provenance='BASELINE'), [], support)['key'] == 'gap'
    assert condition_for(item(status='weak', quality='thin'), [], support)['key'] == 'gap'
    assert condition_for(item(status='uninspected', quality='too_large'), [], support)['key'] == 'unknown'


def test_invented_quote_path_baseline_and_redacted_content_are_rejected():
    assert not assess([candidate(support_quote='Invented evidence not in the snapshot.')]).claim_support
    assert not assess([candidate(support_path='invented.md')]).claim_support
    assert not assess([candidate()], [artifact(provenance='BASELINE')]).claim_support
    assert not assess([candidate()], [artifact(content_excerpt=QUOTE + ' sk-' + 'x' * 24)]).claim_support
    hollow = 'TODO: fill in an estimate and its owner after the team meets.'
    assert not assess([candidate(support_quote=hollow)], [artifact(content_excerpt=hollow)]).claim_support


def test_long_artifact_low_confidence_and_old_snapshot_fall_back():
    long_support = assess([candidate()], [artifact(size=9000)]).claim_support
    assert long_support[0]['judgment'] == 'okay'
    assert not assess([candidate(confidence='low')]).claim_support
    old = {'items': [item()], 'findings': []}
    assert decorate_conditions(old)['items'][0]['condition']['key'] == 'verify'


def test_equivalent_source_concern_prevents_positive_label():
    alt = 'docs/decisions/estimate-record.md'
    support = assess([candidate(support_path=alt)], [artifact(path=alt)]).claim_support
    expected = item(status='equivalent', equivalent_path=alt)
    assert condition_for(expected, [], support)['key'] == 'okay'
    finding = {'id': 'F-alt', 'review_scope': 'course_readiness', 'severity': 3,
               'evidence_refs': ['PATH:' + alt], 'lifecycle': {'status': 'open'}}
    assert condition_for(expected, [finding], support)['key'] == 'concern'


def test_multiple_artifacts_conflict_disputed_stays_visible():
    support = assess([candidate()]).claim_support
    finding = {'id': 'contradiction', 'review_scope': 'both', 'severity': 4,
               'evidence_refs': ['PATH:docs/planning/schedule.md', 'PATH:' + PATH],
               'lifecycle': {'status': 'evidence_disputed'}}
    assert condition_for(item(), [finding], support)['key'] == 'concern'


def test_positive_observations_use_the_same_current_conditions_as_cards():
    from types import SimpleNamespace
    from apps.api.app.services.board_readiness import build_board_readout
    from apps.api.app.services.challenge_engine import ChallengeEngine
    support = assess([candidate()]).claim_support
    evidence = SimpleNamespace(items=[SimpleNamespace(**item())], findings=[],
                               challenge_candidates=[], claim_support=support,
                               strengths=['The starter scaffold is present.'],
                               repository_metrics={})
    expected = supported_observations(evidence)
    assert len(expected) == 1 and 'Strong support' in expected[0]
    assert 'Boundary:' in expected[0]
    assert build_board_readout('A2', evidence)['strengths'] == expected
    assert expected[0] in ChallengeEngine(ai=object()).start('A2', evidence).prompt
    evidence.findings = [{'id': 'F', 'review_scope': 'both', 'severity': 3,
                          'evidence_refs': ['PATH:' + PATH],
                          'lifecycle': {'status': 'evidence_disputed'}}]
    assert supported_observations(evidence) == []
    assert build_board_readout('A2', evidence)['strengths'] == []
    assert supported_observations({'items': [item()], 'findings': [], 'strengths': ['Scaffold']}) == []


def test_defined_and_equivalent_support_stay_bounded_in_board_opening():
    from types import SimpleNamespace
    from apps.api.app.services.challenge_engine import ChallengeEngine
    support = assess([candidate(support_kind='defined', judgment='strong')]).claim_support
    evidence = SimpleNamespace(items=[SimpleNamespace(**item())], findings=[],
                               challenge_candidates=[], claim_support=support,
                               strengths=['Unvalidated praise'], repository_metrics={})
    opening = ChallengeEngine(ai=object()).start('A2', evidence).prompt
    assert 'Okay support' in opening and 'Strong support' not in opening
    assert 'reasonably strong shape' not in opening
    evidence.items = [SimpleNamespace(**item(status='equivalent', equivalent_path=PATH))]
    assert supported_observations(evidence)[0].startswith('Okay support')


def test_current_evidence_api_decorates_saved_claim_without_exposing_full_content():
    import json
    from fastapi.testclient import TestClient
    from apps.api.app.main import app
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import EvidenceSnapshot

    client = TestClient(app)
    seed = client.post('/api/v1/dev/seed').json()
    support = assess([candidate()]).claim_support
    with SessionLocal() as db:
        row = EvidenceSnapshot(
            team_id=seed['team_id'], phase_id='A2', source='demo',
            commit_sha='positive-claim-fixture',
            summary_json=json.dumps({'items': [item()], 'findings': [],
                                     'claim_support': support,
                                     'artifacts': [{**artifact(), 'review_content': 'PRIVATE_FULL_TEXT'}]}),
        )
        db.add(row)
        db.commit()
    response = client.get('/api/v1/reviews/evidence/current', params={
        'team_id': seed['team_id'], 'phase_id': 'A2',
    })
    assert response.status_code == 200, response.text
    evidence = response.json()['evidence']
    assert evidence['items'][0]['condition']['key'] == 'strong'
    assert evidence['items'][0]['condition']['support']['support_path'] == PATH
    assert 'PRIVATE_FULL_TEXT' not in response.text


def test_snapshot_roundtrip_keeps_claim_support_and_legacy_snapshot_works():
    from apps.api.app.services.evidence import (
        ANALYSIS_CONTRACT, snapshot_from_dict, supports_current_analysis_contract,
    )
    support = assess([candidate()]).claim_support
    base = {'phase_id': 'A2', 'repo_full_name': 'team/repo', 'commit_sha': 'frozen',
            'items': [{**item(), 'ref': 'EV-001', 'kind': 'repository',
                       'detail': 'A2 estimate evidence'}],
            'findings': [], 'artifacts': [artifact()]}
    assert snapshot_from_dict({**base, 'claim_support': support}).to_dict()['claim_support'] == support
    assert snapshot_from_dict(base).to_dict()['claim_support'] == []
    assert not supports_current_analysis_contract(base)
    assert not supports_current_analysis_contract({**base, 'semantic_review': {'enabled': True}})
    assert supports_current_analysis_contract({**base, 'semantic_review': {
        'enabled': False, 'analysis_contract': ANALYSIS_CONTRACT,
    }})
