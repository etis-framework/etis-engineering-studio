"""Reviewer directives must not be displayed as the Finding Review opening."""
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.db import Base, engine

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    assert client.post('/api/v1/dev/seed').status_code == 200


@pytest.mark.parametrize('intent', ['challenge', 'resolve', 'discuss', 'understand', 'review'])
def test_finding_opening_is_for_student_and_keeps_selected_finding(intent):
    base = client.post('/api/v1/reviews/start', json={
        'team_id': 1, 'user_id': 2, 'phase_id': 'A1', 'mode': 'board_review',
        'repo_full_name': 'demo/comp330-f26-team-01',
    }).json()
    finding = base['evidence']['findings'][0]
    response = client.post('/api/v1/reviews/start', json={
        'team_id': 1, 'user_id': 2, 'phase_id': 'A1',
        'mode': 'finding_review', 'finding_ids': [finding['id']],
        'entry_intent': intent, 'repo_full_name': 'demo/comp330-f26-team-01',
    })
    assert response.status_code == 200, response.text
    result = response.json()
    message = result['opening']['text'] if 'opening' in result else result['challenge']['opening_text']
    assert finding['title'] in message
    assert finding['statement'] in message
    assert result['challenge']['finding']['id'] == finding['id']
    for directive in ('Start by stating', 'Invite the student', 'Do not defend',
                      'Start with this finding only', 'The student believes',
                      'The student accepts', 'Teach directly'):
        assert directive not in message
    if intent == 'challenge':
        assert 'What did we miss?' in message
        assert 'specific file' in message
