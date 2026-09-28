from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def test_new_review_does_not_silently_complete_an_open_review():
    seed = client.post('/api/v1/dev/seed').json()
    request = {
        'team_id': seed['team_id'], 'user_id': seed['user_id'],
        'phase_id': 'A1', 'mode': 'board_review',
    }
    original = client.post('/api/v1/reviews/start', json=request)
    assert original.status_code == 200, original.text
    original_id = original.json()['session_id']

    another = client.post('/api/v1/reviews/start', json=request)
    assert another.status_code == 200, another.text
    assert another.json()['session_id'] != original_id
    assert client.get(f'/api/v1/reviews/{original_id}').json()['session']['status'] == 'active'

    finished = client.post(f'/api/v1/reviews/{original_id}/complete')
    assert finished.status_code == 200, finished.text
    assert finished.json()['status'] == 'completed'
    assert client.get(f'/api/v1/reviews/{original_id}').json()['session']['status'] == 'completed'
    assert client.get(f"/api/v1/reviews/{another.json()['session_id']}").json()['session']['status'] == 'active'


def test_finish_action_is_in_conversation_and_handoff_uses_existing_evidence():
    html = (ROOT / 'apps/api/app/static/index.html').read_text()
    js = (ROOT / 'apps/api/app/static/studio.js').read_text()
    status = html[html.index('id="reviewStatus"'):html.index('id="activeReviewer"')]
    controls = html[html.index('id="conversationControls"'):html.index('class="composer"')]
    assert 'id="completeReview"' not in status
    assert controls.count('id="completeReview"') == 1
    assert 'id="startAnotherReview"' in controls
    assert 'id="reviewExitOverlay"' in html
    assert 'if(sessionId&&document.body.classList.contains(\'review-session-active\')&&!allowActive)' in js
    assert 'const finding=currentChallenge?.finding' in js
    assert "(currentEvidence?.artifacts||[]).find(a=>a.path===path)" in js
    assert 'No current grade' not in js
