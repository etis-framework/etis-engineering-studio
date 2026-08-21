import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.services.ai_provider import CONVERSATION_SCHEMA
from apps.api.app.services.challenge_engine import Challenge, ChallengeEngine, default_memory

client = TestClient(app)


def _seed_and_start():
    seed = client.post('/api/v1/dev/seed').json()
    r = client.post('/api/v1/reviews/start', json={
        'team_id': seed['team_id'], 'user_id': seed['user_id'], 'phase_id': 'A1', 'mode': 'board_review'
    })
    assert r.status_code == 200
    return seed, r.json()


def test_student_nav_renames_evidence_workspace_and_recommendation_language():
    html = Path('apps/api/app/static/index.html').read_text()
    assert '<span>Engineering Evidence</span>' in html
    assert 'State My Recommendation' in html
    assert 'Commit My Position' not in html
    assert 'Build my recommendation' in html
    assert 'View Evidence' not in html or 'View Evidence' in Path('apps/api/app/static/studio.js').read_text()


def test_engineering_evidence_workspace_has_interactive_surfaces():
    html = Path('apps/api/app/static/index.html').read_text()
    js = Path('apps/api/app/static/studio.js').read_text()
    for marker in ['engineeringEvidenceSummary','engineeringEvidenceStrengths','evidenceLensDetail','engineeringEvidenceInventory','engineeringEvidenceFindings','engineeringTraceability']:
        assert marker in html
    for behavior in ['configureFocusedFromEvidence','configureFindingFromEvidence','renderEngineeringEvidence','loadEngineeringEvidence']:
        assert behavior in js
    assert 'id="artifactExternalLink"' in html
    assert 'target="_blank" rel="noopener noreferrer"' in html


def test_current_evidence_endpoint_returns_same_frozen_snapshot():
    seed, started = _seed_and_start()
    first_id = started['session_id']
    first = client.get(f"/api/v1/reviews/{first_id}").json()
    snapshot_id = first['state']['evidence_snapshot_id']
    current = client.get(f"/api/v1/reviews/evidence/current?team_id={seed['team_id']}&phase_id=A1")
    assert current.status_code == 200
    data = current.json()
    assert data['available'] is True
    assert data['snapshot_id'] == snapshot_id
    # A second review at the same commit/phase should reuse the same immutable snapshot object.
    client.post(f"/api/v1/reviews/{first_id}/complete")
    second = client.post('/api/v1/reviews/start', json={
        'team_id': seed['team_id'], 'user_id': seed['user_id'], 'phase_id': 'A1', 'mode': 'focused_review',
        'focus': 'review our team governance evidence'
    })
    assert second.status_code == 200
    second_detail = client.get(f"/api/v1/reviews/{second.json()['session_id']}").json()
    assert second_detail['state']['evidence_snapshot_id'] == snapshot_id


def test_review_mode_and_continuity_rules_are_in_semantic_prompt():
    engine = ChallengeEngine(ai=type('NoAI', (), {'available': lambda self: False})())
    challenge = Challenge('c','A1','evidence_auditor','t','p','why',[],[],'move')
    memory = default_memory('evidence_auditor')
    memory.update({'review_mode':'focused_review','review_focus':'our risk register','prior_sessions':[{'phase_id':'A1','challenge_title':'Prior review'}]})
    prompt = engine._semantic_system_prompt(challenge, {}, memory, None, 'Alex Rivera', 'consequence_visible', [])
    low = prompt.lower()
    for phrase in ['focused review like office hours','honest evidence-grounded professional opinion','finding review','prior student sessions','product confusion is not engineering weakness','work-in-progress']:
        assert phrase in low


def test_schema_supports_consultative_session_intents():
    intents=set(CONVERSATION_SCHEMA['properties']['student_intent']['enum'])
    assert {'senior_opinion_request','resolution_help','new_session_focus'} <= intents


def test_wargame_corpus_is_broader_for_esl_artifact_and_cross_session_behavior():
    rows=json.loads(Path('evals/student_behavior_cases.json').read_text())
    ids={r['id'] for r in rows}
    assert len(rows) >= 105
    assert {'artifact-honest-opinion','esl-artifact-opinion','cultural-direct-opinion','student-combative-finding','student-alt-file-name','student-new-evidence-after-session','student-apologizes-language','student-asks-end-session'} <= ids
    staff=json.loads(Path('evals/teaching_staff_cases.json').read_text())
    assert len(staff) >= 28
    assert {'ta-esl-confused-ui','instructor-two-sections-drift','instructor-student-esl-not-penalized'} <= {r['id'] for r in staff}
