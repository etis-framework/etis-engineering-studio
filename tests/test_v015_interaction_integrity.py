from pathlib import Path
import json

from fastapi.testclient import TestClient

from apps.api.app.main import app
from apps.api.app.db import Base, engine

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client.post('/api/v1/dev/seed')


def _start(**extra):
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


def test_contextual_finding_review_uses_the_exact_selected_finding():
    board = _start()
    findings = board['evidence']['findings']
    assert len(findings) >= 2
    selected = findings[1]
    other = findings[0]

    focused = _start(
        mode='finding_review',
        finding_ids=[selected['id']],
        entry_intent='resolve',
        source_view='engineering_evidence',
    )
    challenge = focused['challenge']
    text = ' '.join([
        challenge.get('title', ''),
        challenge.get('prompt', ''),
        challenge.get('opening_text', ''),
        challenge.get('finding', {}).get('title', ''),
    ]).lower()
    assert selected['id'] == challenge['finding']['id']
    assert selected['title'].lower() in text
    assert other['title'].lower() not in challenge.get('title', '').lower()
    assert 'resolve' in text or 'act' in text or 'close' in text or 'improve' in text


def test_contextual_entry_metadata_is_persisted_in_session_state():
    board = _start()
    selected = board['evidence']['findings'][0]
    started = _start(
        mode='finding_review',
        finding_ids=[selected['id']],
        entry_intent='challenge',
        source_view='engineering_evidence',
    )
    detail = client.get(f"/api/v1/reviews/{started['session_id']}")
    assert detail.status_code == 200
    memory = detail.json()['state']['conversation_memory']
    assert memory['entry_intent'] == 'challenge'
    assert memory['source_view'] == 'engineering_evidence'


def test_evidence_dispute_can_target_exact_finding_id():
    started = _start()
    fid = started['evidence']['findings'][0]['id']
    path = started['evidence']['findings'][0]['evidence_refs'][0].replace('PATH:', '')
    r = client.post(
        f"/api/v1/reviews/{started['session_id']}/evidence-dispute",
        json={
            'path': path,
            'finding_id': fid,
            'explanation': 'This exact artifact contains equivalent evidence the board should reconsider.',
        },
    )
    assert r.status_code == 200, r.text


def test_student_ui_has_one_primary_start_action_and_explicit_new_review_home():
    html = (ROOT / 'apps/api/app/static/index.html').read_text()
    assert html.count('id="newReview"') == 1
    assert 'id="reviewHomeButton"' in html
    assert 'New Review Home' in html


def test_ui_context_is_propagated_instead_of_generic_review_start():
    js = (ROOT / 'apps/api/app/static/studio.js').read_text()
    compact = ''.join(js.split())
    assert 'entry_intent:opts.entry_intent' in compact
    assert 'source_view:opts.source_view' in compact
    assert 'finding_id:findingId' in js
    assert 'evidence_refs:contextRefs()' in js
    assert "currentFindingById" in js
    assert "Help me resolve this" in js


def test_open_evidence_requires_an_exact_frozen_artifact_not_a_guessed_url():
    js = (ROOT / 'apps/api/app/static/studio.js').read_text()
    assert 'No exact frozen artifact is available to open' in js
    assert 'showArtifact(art.path' in js
    assert 'artifactExternalLink' in js


def test_navigation_scrolls_contextual_handoffs_to_top():
    js = (ROOT / 'apps/api/app/static/studio.js').read_text()
    assert "window.scrollTo({top:0" in js
    assert "source_view:'engineering_evidence'" in js


def test_drafts_survive_failed_turns_and_refreshes():
    js = (ROOT / 'apps/api/app/static/studio.js').read_text()
    for token in ('function saveDraft()', 'function restoreDraft()', 'sessionStorage.setItem', 'Your unsent draft was restored.'):
        assert token in js


def test_wargame_corpora_cover_product_interaction_and_language_outliers():
    students = json.loads((ROOT / 'evals/student_behavior_cases.json').read_text())
    staff = json.loads((ROOT / 'evals/teaching_staff_cases.json').read_text())
    ui = json.loads((ROOT / 'evals/ui_interaction_cases.json').read_text())
    assert len(students) >= 140
    assert len(staff) >= 40
    assert len(ui) >= 50
    student_ids = {x['id'] for x in students}
    for expected in {
        'esl-ambiguous-pronoun-context',
        'esl-literal-ownership',
        'student-hostile-but-substantive',
        'student-prior-session-new-review',
        'student-slow-response-repeat',
        'student-help-resolve-no-idea',
    }:
        assert expected in student_ids


def test_respond_expands_selected_artifact_from_frozen_snapshot(monkeypatch):
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import EvidenceSnapshot, ReviewSession
    from apps.api.app.routers import reviews as reviews_router

    started = _start(phase_id="A2")
    session_id = started["session_id"]

    db = SessionLocal()
    try:
        session = db.get(ReviewSession, session_id)
        state = json.loads(session.challenge_state_json)
        snapshot = db.get(EvidenceSnapshot, state["evidence_snapshot_id"])

        frozen = json.loads(snapshot.summary_json)
        frozen["artifacts"] = [
            {
                "path": "docs/planning/README.md",
                "provenance": "TEAM_ADAPTED",
                "quality": "reviewable",
                "summary": "Planning README.",
                "content_excerpt": "SHORT EXCERPT",
                "review_content": (
                    "README START\n"
                    + ("authoritative planning detail\n" * 150)
                    + "README END"
                ),
            },
            {
                "path": "docs/planning/other.md",
                "provenance": "TEAM_ADAPTED",
                "quality": "reviewable",
                "summary": "Other planning artifact.",
                "content_excerpt": "UNRELATED EXCERPT",
                "review_content": "UNRELATED FULL CONTENT",
            },
        ]
        snapshot.summary_json = json.dumps(frozen)
        db.commit()
    finally:
        db.close()

    captured = {}

    def fake_converse(*args, **kwargs):
        captured["evidence_context"] = kwargs.get("evidence_context", "")
        return (
            {
                "text": "I reviewed the selected frozen artifact.",
                "lens": "evidence_auditor",
                "provider": "deterministic-test",
                "kind": "coaching",
                "reviewer": {"name": "Maya Chen", "role": "Evidence Auditor"},
                "target_move": "evidence_traceable",
                "guidance_refs": [],
                "teach_back": False,
            },
            {},
            {"signals": {}, "ready_to_commit": False},
        )

    monkeypatch.setattr(reviews_router.engine, "converse", fake_converse)

    response = client.post(
        f"/api/v1/reviews/{session_id}/respond",
        json={
            "response": "What is strong, weak, or missing from this README?",
            "evidence_refs": ["PATH:docs/planning/README.md"],
            "decision": None,
            "intent": "discuss",
            "client_turn_id": "selected-artifact-regression-001",
        },
    )

    assert response.status_code == 200, response.text

    context = captured["evidence_context"]
    assert "docs/planning/README.md" in context
    assert "README START" in context
    assert "README END" in context
    assert "authoritative planning detail" in context
    assert "UNRELATED FULL CONTENT" not in context


def test_evidence_ask_board_submits_immediately_in_active_review():
    js = (ROOT / 'apps/api/app/static/studio.js').read_text()
    compact = ''.join(js.split())

    # "Ask reviewer" sends within an active review, while retaining an
    # unfinished student draft rather than overwriting it.
    assert "if(sessionId&&document.body.classList.contains('review-session-active')){" in compact
    assert "if(els.response.value.trim()){els.response.focus();" in compact
    assert "constsending=send();" in compact
    assert "awaitsending;" in compact

    # Explicit artifact attachment remains a manual next-message action.
    assert "Evidenceattachedtoyournextmessage." in compact
