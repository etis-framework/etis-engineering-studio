"""A first-time student can follow the current exchange and challenge honestly."""

from pathlib import Path
import shutil
import subprocess

import pytest

from apps.api.app.routers.reviews import _ai_nonuse_dispute_reply


ROOT = Path('apps/api/app/static')
HTML = (ROOT / 'index.html').read_text()
CSS = (ROOT / 'studio.css').read_text()
JS = (ROOT / 'studio.js').read_text()


def test_reply_is_the_next_action_in_active_review_at_every_width():
    conversation = HTML.index('id="transcript"')
    reply = HTML.index('id="replyLabel"')
    textarea = HTML.index('id="response"')
    send = HTML.index('id="send"')
    optional_modes = HTML.index('id="conversationControls"')
    finish = HTML.index('id="completeReview"')
    assert conversation < reply < textarea < send < optional_modes < finish
    assert 'for="response"' in HTML
    assert 'updateReplyInvitation()' in JS
    assert '.review-session-active .review-finish{position:static' in CSS
    assert '@media(max-width:850px){.review-session-active .conversation-controls{grid-template-columns:1fr}' in CSS


def test_new_and_returning_students_are_told_which_room_holds_what():
    assert 'You can move between rooms without ending a review.' in HTML
    assert 'Selecting a review type does not start a session.' in HTML
    assert 'role="status"' in HTML[HTML.index('id="evidenceSnapshotNote"'):][:100]
    assert 'SAVED SNAPSHOT FINDINGS' in HTML
    assert 'Current review evidence' in HTML
    assert "$('#evCoverage').textContent='No review open'" in JS
    assert 'Frozen copy saved ${snapshotCaptureLabel(payload.created_at)}' in JS


def test_nonuse_question_gets_bounded_help_without_claiming_proof():
    path = 'docs/ai/ai-use-log.md'
    for student in ('No AI is used, why do I need this file?',
                    'We have not used AI yet. What do we record?',
                    'AI was never used by our team.',
                    "AI wasn't used by the team."):
        answer = _ai_nonuse_dispute_reply(path, student)
        assert answer and 'do not need to invent' in answer
        assert 'period' in answer and 'team attestation' in answer
        assert 'empty table alone cannot establish non-use' in answer
    assert _ai_nonuse_dispute_reply(path, 'We used AI for risk analysis') is None
    assert _ai_nonuse_dispute_reply('docs/planning/scope.md', 'No AI used') is None


@pytest.mark.skipif(not shutil.which('node'), reason='Node needed for UI-state simulation')
def test_reply_invitation_follows_reviewer_and_disappears_in_history():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const fn=source.slice(source.indexOf('function updateReplyInvitation('),
                      source.indexOf('function hideActiveReviewer(',source.indexOf('function updateReplyInvitation(')));
for (const [active,reviewer,expected] of [
 [true,{name:'Maya Chen'},'Your turn — reply to Maya'],
 [true,{name:'Priya Nair'},'Your turn — reply to Priya'],
 [true,null,'Your turn — reply to your reviewer'],
 [false,{name:'Maya Chen'},null],
]) {
 const visible=new Set(),label={classList:{toggle:(x,on)=>on?visible.add(x):visible.delete(x)}},
   cue={classList:{toggle:(x,on)=>on?visible.add(x):visible.delete(x)}};
 const ctx={sessionId:active?12:null,currentReviewer:reviewer,
 document:{body:{classList:{contains:()=>active}}},$:id=>id==='#replyLabel'?label:cue};
 vm.runInNewContext(fn+';updateReplyInvitation()',ctx);
 assert.strictEqual(visible.has('hidden'),!active);
 if(expected)assert.strictEqual(label.textContent,expected);
}
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


def test_ai_nonuse_dispute_reply_is_recorded_and_retry_returns_same_answer():
    from fastapi.testclient import TestClient
    from apps.api.app.db import Base, engine
    from apps.api.app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client = TestClient(app)
    assert client.post('/api/v1/dev/seed').status_code == 200
    started = client.post('/api/v1/reviews/start', json={
        'team_id': 1, 'user_id': 2, 'phase_id': 'A2',
        'mode': 'board_review', 'repo_full_name': 'demo/comp330-f26-team-01',
    })
    assert started.status_code == 200
    sid = started.json()['session_id']
    request = {'path': 'docs/ai/ai-use-log.md',
               'explanation': 'No AI is used, why do we need this file?',
               'client_turn_id': 'nonuse-2026-09-30'}
    response = client.post(f'/api/v1/reviews/{sid}/evidence-dispute', json=request)
    assert response.status_code == 200, response.text
    assert response.json()['disposition'] == 'artifact_found'
    answer = response.json()['reply']['text']
    assert 'do not need to invent log entries' in answer
    assert 'empty table alone cannot establish non-use' in answer
    assert 'team attestation' in answer
    again = client.post(f'/api/v1/reviews/{sid}/evidence-dispute', json=request)
    assert again.status_code == 200
    assert again.json()['duplicate'] is True
    assert again.json()['reply']['text'] == answer
