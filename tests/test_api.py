import json
from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.routers import reviews as reviews_router
from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.db import SessionLocal
from apps.api.app.models import ReviewSession, ReviewTurn

client = TestClient(app)


class FakeSemanticProvider:
    """Offline test double for the semantic provider contract.

    It is intentionally only a protocol test double. Production semantic understanding
    is supplied by the configured model and Structured Outputs, not these test rules.
    """
    def available(self):
        return True

    def reviewer_turn(self, system_prompt, user_prompt):
        lower = user_prompt.lower()
        updates = {
            "consequence_visible": False,
            "evidence_boundary_visible": False,
            "decision_explicit": False,
            "boundary_visible": False,
            "ownership_visible": False,
            "change_trigger_visible": False,
            "uncertainty_visible": False,
            "tradeoff_visible": False,
        }
        intent = "reasoning"
        mode = "coach"
        teach = False
        reply = "Tell me one more thing about the engineering consequence."
        points = []
        next_target = "consequence_visible"

        if "finger pointing?" in lower or "finger pointing" in lower:
            intent = "tentative_reasoning" if "finger pointing?" in lower else "reasoning"
            updates["consequence_visible"] = True
            points = ["The student identified finger-pointing as a consequence of unclear working rules."]
            reply = "Yes—that is a plausible consequence. If disagreement is not governed, it can turn into finger-pointing and unclear corrective ownership. What can the team defend from the repository today, and what still is not supported?"
            next_target = "evidence_boundary_visible"
        if "support structure" in lower or "roles are defined" in lower or "conflict resolution" in lower:
            updates["evidence_boundary_visible"] = True
            points = ["The student distinguished role/structure evidence from unsupported conflict-resolution governance."]
            reply = "Right. You have separated two different claims: the repository can show role structure, but it cannot yet prove how the team will resolve disagreements. Given that gap, what do you recommend the team do now?"
            next_target = "decision_explicit"
        if "i do not know" in lower or "tell me the answer" in lower or "i need another nudge" in lower:
            intent = "answer_seeking" if "tell me" in lower else "stuck"
            mode = "teach"
            teach = True
            reply = "You have worked at this long enough, so let me teach this piece directly. `roles.md` can support who owns responsibilities. A working agreement supports how the team coordinates, reviews work, handles disagreement, and escalates problems. A reasonable A1 position is to continue low-risk setup work with conditions, but not claim that collaboration/conflict-resolution governance is established until the working agreement is reviewed, agreed, and visible. In your own words, what is the difference between roles and working agreements?"
            next_target = "decision_explicit"
        return {
            "student_intent": intent,
            "understood_points": points,
            "reasoning_updates": updates,
            "stuck": intent == "stuck",
            "frustrated": False,
            "needs_direct_teaching": teach,
            "response_mode": mode,
            "next_target": next_target,
            "reply": reply,
            "guidance_ids": ["ETIS-ES100-PRINCIPLES"] if teach else [],
            "handoff_lens": None,
            "teach_back": teach,
            "provider": "fake-semantic",
            "model": "test-model",
        }

    def critique_reviewer_turn(self, system_prompt, user_prompt):
        return {"acceptable": True, "issues": [], "revised_reply": "", "provider": "fake-semantic", "model": "test-model"}

    def validate_reasoning_turn(self, system_prompt, user_prompt):
        payload = json.loads(user_prompt)
        evaluations = []
        for dimension in payload.get("candidate_transitions", []):
            if dimension == "consequence_visible":
                evaluations.append({
                    "dimension": dimension,
                    "decision": "REJECT",
                    "reason_codes": ["TOO_VAGUE_TO_ESTABLISH"],
                    "evidence_refs": [],
                    "summary": "The shadow validator does not accept this consequence claim.",
                })
            else:
                evaluations.append({
                    "dimension": dimension,
                    "decision": "ACCEPT",
                    "reason_codes": ["STUDENT_REASONING_EXPLICIT"],
                    "evidence_refs": [],
                    "summary": "The shadow validator accepts this proposed transition.",
                })
        return {
            "evaluations": evaluations,
            "reopens": [],
            "provider": "fake-validator",
            "model": "validator-model",
            "response_id": "validator-response",
        }


def use_fake_semantic():
    reviews_router.engine.ai = FakeSemanticProvider()


def test_health():
    with client:
        r = client.get('/health')
        assert r.status_code == 200
        assert r.json()['status'] == 'ok'
        assert r.json()['version'] == '0.16.1'
        assert r.json()['reasoning_validation_mode'] in {'legacy', 'shadow'}
        assert 'reasoning_validator_model' in r.json()


def test_course_endpoint():
    with client:
        r = client.get('/api/v1/course')
        assert r.status_code == 200
        assert len(r.json()['phases']) == 6


def _start_a1():
    seed = client.post('/api/v1/dev/seed').json()
    started = client.post('/api/v1/reviews/start', json={"team_id": seed["team_id"], "phase_id": "A1", "user_id": seed["user_id"]})
    assert started.status_code == 200
    payload = started.json()
    assert payload['challenge']['reviewer']['name'] in {'Maya Chen', 'Marcus Reed', 'Priya Nair', 'Elena Torres'}
    return seed, payload


def test_semantic_provider_is_required_for_conversation(monkeypatch):
    _, started = _start_a1()
    sid = started['session_id']
    class Unavailable:
        def available(self): return False
    old = reviews_router.engine.ai
    reviews_router.engine.ai = Unavailable()
    try:
        r = client.post(f'/api/v1/reviews/{sid}/respond', json={"response":"finger pointing?", "evidence_refs":[], "decision":None, "intent":"discuss"})
        assert r.status_code == 503
        assert r.json()['code'] == 'semantic_coaching_unavailable'
    finally:
        reviews_router.engine.ai = old


def test_tentative_answer_with_question_mark_is_reasoning_not_clarification():
    use_fake_semantic()
    _, started = _start_a1()
    sid = started['session_id']
    r = client.post(f'/api/v1/reviews/{sid}/clarify', json={"question":"finger pointing?"})
    assert r.status_code == 200
    data = r.json()
    assert data['reply']['interpreted_intent'] == 'tentative_reasoning'
    assert data['reasoning_state']['consequence_visible'] is True
    assert 'plausible consequence' in data['reply']['text'].lower()


def test_semantic_meaning_counts_without_magic_words():
    use_fake_semantic()
    _, started = _start_a1()
    sid = started['session_id']
    client.post(f'/api/v1/reviews/{sid}/respond', json={"response":"finger pointing", "evidence_refs":[], "decision":None, "intent":"discuss"})
    r = client.post(f'/api/v1/reviews/{sid}/respond', json={"response":"it can support structure, but it can not support conflict resolution", "evidence_refs":[], "decision":None, "intent":"discuss"})
    assert r.status_code == 200
    data = r.json()
    assert data['evaluation']['signals']['evidence_boundary_visible'] is True
    assert 'separated two different claims' in data['follow_up']['text'].lower()


def test_stuck_student_is_taught_directly_and_given_teach_back():
    use_fake_semantic()
    _, started = _start_a1()
    sid = started['session_id']
    r = client.post(f'/api/v1/reviews/{sid}/respond', json={"response":"I do not know", "evidence_refs":[], "decision":None, "intent":"discuss"})
    assert r.status_code == 200
    data = r.json()
    assert data['follow_up']['teach_back'] is True
    assert data['follow_up']['kind'] == 'teaching'
    assert 'let me teach this piece directly' in data['follow_up']['text'].lower()
    assert data['follow_up']['guidance_refs']


def test_answer_seeking_is_answered_not_stonewalled():
    use_fake_semantic()
    _, started = _start_a1()
    sid = started['session_id']
    r = client.post(f'/api/v1/reviews/{sid}/respond', json={"response":"tell me the answer", "evidence_refs":[], "decision":None, "intent":"discuss"})
    assert r.status_code == 200
    text = r.json()['follow_up']['text'].lower()
    assert 'reasonable a1 position' in text
    assert 'in your own words' in text


def test_review_history_and_instructor_detail_still_work():
    use_fake_semantic()
    seed, started = _start_a1()
    sid = started['session_id']
    history = client.get(f"/api/v1/reviews?team_id={seed['team_id']}&user_id={seed['user_id']}")
    assert history.status_code == 200
    assert any(x['id'] == sid for x in history.json()['sessions'])
    detail = client.get(f"/api/v1/instructor/teams/{seed['team_id']}")
    assert detail.status_code == 200


def test_opening_is_personalized_and_one_question_at_a_time():
    _, started = _start_a1()
    opening = started['challenge']['opening_text']
    opening_lower = opening.lower()

    assert opening.startswith('Alex,')
    assert 'scaffold' in opening_lower
    # The exact engineering challenge is intentionally selected from the current
    # repository findings.  Test the UX contract rather than a canned sentence:
    # a personalized, strengths-first opening that asks one focused question.
    assert opening.count('?') == 1
    assert any(term in opening_lower for term in ('evidence','workflow','control','claim','consequence'))
    assert 'who owns the next action' not in opening_lower


def test_review_start_retry_reuses_same_persisted_review_objective():
    seed = client.post('/api/v1/dev/seed').json()
    body = {
        "team_id": seed["team_id"],
        "phase_id": "A1",
        "user_id": seed["user_id"],
        "client_request_id": "pr1-objective-retry-001",
    }

    first = client.post('/api/v1/reviews/start', json=body)
    second = client.post('/api/v1/reviews/start', json=body)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()['session_id'] == second.json()['session_id']
    assert second.json()['duplicate'] is True

    detail = client.get(f"/api/v1/reviews/{first.json()['session_id']}")
    assert detail.status_code == 200, detail.text
    objective = detail.json()['state']['review_control']['objective']
    assert objective['objective_id']

    detail_again = client.get(f"/api/v1/reviews/{second.json()['session_id']}")
    objective_again = detail_again.json()['state']['review_control']['objective']
    assert objective_again['objective_id'] == objective['objective_id']


def test_shadow_reasoning_validation_records_disagreement_without_changing_legacy_behavior():
    use_fake_semantic()
    old_mode = reviews_router.engine.settings.etis_reasoning_validation_mode
    reviews_router.engine.settings.etis_reasoning_validation_mode = "shadow"
    try:
        _, started = _start_a1()
        sid = started["session_id"]
        # Session-locked shadow mode must survive a later deployment-default change.
        reviews_router.engine.settings.etis_reasoning_validation_mode = "legacy"
        response = client.post(
            f"/api/v1/reviews/{sid}/respond",
            json={
                "response": "finger pointing?",
                "evidence_refs": [],
                "decision": None,
                "intent": "discuss",
                "client_turn_id": "shadow-turn-1",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["evaluation"]["learning_score"] >= 1
        assert "_reasoning_proposals" not in payload["follow_up"]
        assert "_reasoning_proposal_intent" not in payload["follow_up"]

        review = client.get(f"/api/v1/reviews/{sid}").json()
        assert review["state"]["reasoning_state"]["consequence_visible"] is True
        assert review["state"]["review_control"]["reasoning_mode"] == "shadow"
        assert "reasoning_shadow" not in review["state"]["review_control"]
        assert all(
            "reasoning_validation_shadow" not in turn["signals"]
            for turn in review["turns"]
        )

        with SessionLocal() as db:
            session = db.get(ReviewSession, sid)
            persisted_state = json.loads(session.challenge_state_json)
            shadow = persisted_state["review_control"]["reasoning_shadow"]
            assert shadow["dimensions"]["consequence_visible"]["status"] == "unestablished"
            assert shadow["last_validation"]["status"] == "completed"
            assert shadow["last_validation"]["evaluations"][0]["decision"] == "REJECT"
            student_turn = (
                db.query(ReviewTurn)
                .filter_by(session_id=sid, client_turn_id="shadow-turn-1")
                .one()
            )
            signals = json.loads(student_turn.signals_json)
            assert signals["reasoning_validation_shadow"]["status"] == "completed"
    finally:
        reviews_router.engine.settings.etis_reasoning_validation_mode = old_mode


def test_legacy_reasoning_mode_never_invokes_shadow_validator():
    class LegacyOnlyProvider(FakeSemanticProvider):
        def validate_reasoning_turn(self, system_prompt, user_prompt):
            raise AssertionError("shadow validator must not run for legacy sessions")

    old_provider = reviews_router.engine.ai
    old_mode = reviews_router.engine.settings.etis_reasoning_validation_mode
    reviews_router.engine.ai = LegacyOnlyProvider()
    reviews_router.engine.settings.etis_reasoning_validation_mode = "legacy"
    try:
        _, started = _start_a1()
        sid = started["session_id"]
        # A later default change to shadow must not change this active legacy session.
        reviews_router.engine.settings.etis_reasoning_validation_mode = "shadow"
        response = client.post(
            f"/api/v1/reviews/{sid}/respond",
            json={
                "response": "finger pointing?",
                "evidence_refs": [],
                "decision": None,
                "intent": "discuss",
                "client_turn_id": "legacy-no-shadow",
            },
        )
        assert response.status_code == 200
        review = client.get(f"/api/v1/reviews/{sid}").json()
        assert review["state"]["review_control"]["reasoning_mode"] == "legacy"
        assert "reasoning_shadow" not in review["state"]["review_control"]
    finally:
        reviews_router.engine.ai = old_provider
        reviews_router.engine.settings.etis_reasoning_validation_mode = old_mode
