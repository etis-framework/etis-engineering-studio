from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.services.artifact_condition import condition_for


def item(status='present', quality='reviewable', **extra):
    return {'title': extra.pop('title', 'docs/planning/estimates.md'), 'status': status,
            'quality': quality, 'source_provenance': 'TEAM_ADAPTED', **extra}


def finding(ref='PATH:docs/planning/estimates.md', scope='course_readiness', state='open'):
    return {'id': 'F-1', 'evidence_refs': [ref], 'review_scope': scope,
            'severity': 4, 'lifecycle': {'status': state}}


def test_presence_does_not_mean_supported_and_course_concern_surfaces():
    assert condition_for(item(), [])['key'] == 'verify'
    concern = condition_for(item(), [finding()])
    assert concern['key'] == 'concern'
    assert concern['finding_id'] == 'F-1'
    assert condition_for(item(), [finding(state='corrected')])['key'] == 'verify'


def test_missing_scaffold_weak_and_inspection_boundaries_take_precedence():
    assert condition_for(item(status='missing', quality='missing'), [finding()])['key'] == 'gap'
    assert condition_for(item(status='scaffold', quality='scaffold'), [])['label'] == 'Starter only'
    assert condition_for(item(status='weak', quality='thin'), [finding()])['key'] == 'gap'
    assert condition_for(item(status='uninspected', quality='too_large'), [])['key'] == 'unknown'


def test_equivalent_and_directory_findings_link_without_claiming_quality():
    equivalent = item(status='equivalent', equivalent_path='docs/decisions/plan.md')
    assert condition_for(equivalent, [])['key'] == 'verify'
    linked = condition_for(equivalent, [finding('PATH:docs/decisions/plan.md')])
    assert linked['key'] == 'concern'
    folder = item(title='docs/planning/', status='present')
    assert condition_for(folder, [finding('PATH:docs/planning/estimates.md')])['key'] == 'concern'


def test_professional_challenge_is_not_mislabeled_as_required_remediation():
    condition = condition_for(item(), [finding(scope='professional_challenge')])
    assert condition['key'] == 'explore'
    assert 'not automatically a phase requirement' in condition['why']
    assert condition_for(item(), [finding(state='evidence_disputed')])['key'] == 'concern'


def test_review_api_exposes_condition_without_changing_frozen_quality():
    client = TestClient(app)
    seed = client.post('/api/v1/dev/seed').json()
    started = client.post('/api/v1/reviews/start', json={
        'team_id': seed['team_id'], 'user_id': seed['user_id'],
        'phase_id': 'A1', 'mode': 'board_review',
    })
    assert started.status_code == 200, started.text
    evidence = started.json()['evidence']
    assert evidence['items']
    assert all('condition' in item and 'quality' in item for item in evidence['items'])
    assert all(item['condition']['key'] in {'gap', 'concern', 'unknown', 'verify', 'explore'}
               for item in evidence['items'])
    session_id = started.json()['session_id']
    resumed = client.get(f'/api/v1/reviews/{session_id}').json()['evidence']
    current = client.get('/api/v1/reviews/evidence/current', params={
        'team_id': seed['team_id'], 'phase_id': 'A1',
    }).json()['evidence']
    assert [i['condition'] for i in resumed['items']] == [i['condition'] for i in evidence['items']]
    assert [i['condition'] for i in current['items']] == [i['condition'] for i in evidence['items']]
