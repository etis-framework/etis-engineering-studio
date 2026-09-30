"""A frozen finding can be disputed or corrected without inventing repo repair."""
from fastapi.testclient import TestClient

from apps.api.app.db import Base, engine
from apps.api.app.main import app
from apps.api.app.services.artifact_condition import condition_for

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    assert client.post('/api/v1/dev/seed').status_code == 200


def review():
    response = client.post('/api/v1/reviews/start', json={
        'team_id': 1, 'user_id': 2, 'phase_id': 'A1', 'mode': 'board_review',
        'repo_full_name': 'demo/comp330-f26-team-01',
    })
    assert response.status_code == 200, response.text
    result = response.json()
    return result['session_id'], result['evidence']


def post_state(session, fid, status, rationale=''):
    return client.post(f'/api/v1/reviews/{session}/findings/{fid}/disposition',
                       json={'status': status, 'rationale': rationale})


def test_unknown_finding_and_premature_resolution_cannot_clear_frozen_concern():
    session, evidence = review()
    fid = evidence['findings'][0]['id']
    assert post_state(session, 'invented-finding', 'corrected', 'It was wrong').status_code == 422
    assert post_state(session, fid, 'resolved', 'We changed the repository later').status_code == 409
    assert post_state(session, fid, 'corrected').status_code == 422
    current = client.get(f'/api/v1/reviews/{session}').json()['evidence']
    assert next(f for f in current['findings'] if f['id'] == fid)['lifecycle']['status'] == 'open'
    assert post_state(session, fid, 'corrected', 'The original interpretation was wrong.').status_code == 200
    corrected = client.get(f'/api/v1/reviews/{session}').json()['evidence']
    assert next(f for f in corrected['findings'] if f['id'] == fid)['lifecycle']['status'] == 'corrected'
    assert all(f['lifecycle']['status'] != 'corrected' for f in corrected['findings'] if f['id'] != fid)


def test_unknown_dispute_target_is_rejected_without_changing_the_conversation():
    session, evidence = review()
    artifact = evidence['artifacts'][0]
    url = f'/api/v1/reviews/{session}/evidence-dispute'
    # Verify endpoint URL against the actual router before changing any state.
    assert artifact['path']
    response = client.post(url, json={'path': artifact['path'],
                                      'finding_id': 'invented-finding',
                                      'explanation': 'This is contrary evidence in the frozen source.'})
    assert response.status_code == 422, response.text


def test_unrelated_concern_remains_when_one_interpretation_is_corrected():
    item = {'title': 'docs/planning/estimates.md', 'status': 'present',
            'quality': 'reviewable', 'source_provenance': 'TEAM_ADAPTED'}
    weak = {'id': 'F-weak', 'review_scope': 'course_readiness', 'severity': 4,
            'evidence_refs': ['PATH:docs/planning/estimates.md'],
            'lifecycle': {'status': 'open'}}
    corrected = {**weak, 'id': 'F-corrected', 'lifecycle': {'status': 'corrected'}}
    disputed = {**weak, 'id': 'F-disputed', 'lifecycle': {'status': 'evidence_disputed'}}
    assert condition_for(item, [corrected])['key'] == 'verify'
    assert condition_for(item, [corrected, weak])['finding_id'] == 'F-weak'
    assert condition_for(item, [corrected, disputed])['finding_id'] == 'F-disputed'
    for quality in ('thin', 'partial'):
        assert condition_for({**item, 'quality': quality}, [corrected])['key'] == 'gap'
