"""Exact-path disputes inspect frozen evidence instead of bouncing work to the student."""

from fastapi.testclient import TestClient

from apps.api.app.db import Base, engine as db_engine
from apps.api.app.main import app
from apps.api.app.routers import reviews


class AvailableAI:
    def available(self):
        return True


def test_exact_path_dispute_uses_semantic_reviewer_and_selected_frozen_package(monkeypatch):
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    client = TestClient(app)
    assert client.post('/api/v1/dev/seed').status_code == 200
    started = client.post('/api/v1/reviews/start', json={
        'team_id': 1, 'user_id': 2, 'phase_id': 'A3',
        'mode': 'board_review', 'repo_full_name': 'demo/comp330-f26-team-01',
    })
    assert started.status_code == 200
    sid = started.json()['session_id']

    calls = []

    def fake_converse(challenge, text, prior_state=None, **kwargs):
        calls.append((text, kwargs))
        context = kwargs['evidence_context']
        assert 'docs/architecture/architecture.md' in context
        assert kwargs['intent'] == 'evidence_dispute'
        assert 'PATH:docs/architecture/architecture.md' in kwargs['evidence_refs']
        return ({
            'text': (
                'I inspected the selected frozen architecture file. Its current content is enough '
                'to show where the work should be recorded, but not enough to establish the '
                'architecture baseline. You can start; the baseline is not yet demonstrated.'
            ),
            'lens': 'evidence_auditor',
            'reviewer': {'name': 'Maya Chen', 'role': 'Evidence Auditor'},
            'provider': 'test-semantic',
            'kind': 'conversation',
            'interpreted_intent': 'evidence_dispute',
            'target_move': 'evidence_boundary_visible',
            'guidance_refs': [],
            'coaching_phase': 'A3',
            'teach_back': False,
            'conversation_memory': {'active_lens': 'evidence_auditor'},
            'usage_events': [],
        }, prior_state or {}, {'ready_to_commit': False})

    monkeypatch.setattr(reviews.engine, 'ai', AvailableAI())
    monkeypatch.setattr(reviews.engine, 'converse', fake_converse)
    monkeypatch.setattr(reviews.engine.settings, 'etis_semantic_conversation', True)

    response = client.post(f'/api/v1/reviews/{sid}/evidence-dispute', json={
        'path': 'docs/architecture/architecture.md',
        'explanation': 'We are not this far yet. Do we have enough evidence in the repo to start this?',
        'client_turn_id': 'semantic-inspection-001',
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['disposition'] == 'artifact_found'
    assert calls
    assert body['reply']['provider'] == 'test-semantic'
    assert 'You can start' in body['reply']['text']
    assert 'Which passage' not in body['reply']['text']


def test_challenge_dialogue_copy_explains_that_selected_file_will_be_inspected():
    html = open('apps/api/app/static/index.html', encoding='utf-8').read()
    assert 'Maya will inspect that frozen file' in html
    assert 'or ask what it means for your next step' in html
