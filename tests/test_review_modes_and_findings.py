from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.db import Base, engine

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client.post('/api/v1/dev/seed')


def start(**extra):
    body = {
        'team_id': 1,
        'phase_id': 'A1',
        'user_id': 2,
        'repo_full_name': 'demo/comp330-f26-team-01',
        'mode': 'board_review',
    }
    body.update(extra)
    r = client.post('/api/v1/reviews/start', json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_finding_review_can_target_related_findings():
    d = start()
    ids = [x['id'] for x in d['evidence']['findings'][:2]]
    d2 = start(mode='finding_review', finding_ids=ids)
    assert d2['challenge']['title'].startswith('Finding Review')
    assert len(ids) == 2


def test_finding_disposition_is_recorded():
    d = start()
    fid = d['evidence']['findings'][0]['id']
    r = client.post(
        f"/api/v1/reviews/{d['session_id']}/findings/{fid}/disposition",
        json={'status': 'accepted_risk', 'rationale': 'We understand the limitation and will revisit it before A2.'},
    )
    assert r.status_code == 200
    assert r.json()['status'] == 'accepted_risk'


def test_corrected_finding_is_not_selected_again_on_same_snapshot():
    d = start()
    fid = d['challenge']['finding']['id']
    r = client.post(
        f"/api/v1/reviews/{d['session_id']}/findings/{fid}/disposition",
        json={'status': 'corrected', 'rationale': 'Equivalent evidence was confirmed.'},
    )
    assert r.status_code == 200
    d2 = start()
    assert d2['challenge']['id'] != fid


def test_review_start_rejects_more_than_three_finding_ids():
    r = client.post('/api/v1/reviews/start', json={
        'team_id': 1, 'phase_id': 'A1', 'user_id': 2,
        'repo_full_name': 'demo/comp330-f26-team-01', 'mode': 'finding_review',
        'finding_ids': ['a','b','c','d'],
    })
    assert r.status_code == 422


def test_selected_finding_enters_under_discussion_without_being_confirmed():
    d = start()
    fid = d['evidence']['findings'][0]['id']
    d2 = start(mode='finding_review', finding_ids=[fid])
    target = next(x for x in d2['evidence']['findings'] if x['id'] == fid)
    assert target['lifecycle']['status'] == 'under_discussion'
