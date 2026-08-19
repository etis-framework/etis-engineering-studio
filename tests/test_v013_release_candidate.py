import json
from pathlib import Path

from apps.api.app.services.ai_provider import CONVERSATION_SCHEMA
from apps.api.app.services.challenge_engine import Challenge, ChallengeEngine, default_memory


def test_review_room_has_one_start_button_and_runtime_helpers():
    html = Path('apps/api/app/static/index.html').read_text()
    js = Path('apps/api/app/static/studio.js').read_text()
    assert 'id="newReview"' in html
    assert 'id="startSelectedReview"' not in html
    assert 'function setMode(' in js
    assert 'async function send(' in js
    assert "$('#coachButton').onclick" in js
    assert 'function updateStartReviewButton(' in js
    assert 'window.addEventListener(\'error\'' in js


def test_review_mode_contract_is_single_select_and_session_locked():
    html = Path('apps/api/app/static/index.html').read_text()
    js = Path('apps/api/app/static/studio.js').read_text()
    assert html.count('data-review-mode=') == 3
    assert 'aria-pressed="true"' in html
    assert "if(sessionId){toast('This review keeps its purpose." in js
    assert "Start Focused Review" in js
    assert "Start Finding Review" in js
    assert "Start Board Review" in js


def test_behavior_corpus_includes_international_and_adversarial_cases():
    rows = json.loads(Path('evals/student_behavior_cases.json').read_text())
    assert len(rows) >= 75
    ids = {r['id'] for r in rows}
    required = {
        'esl-final-say','literal-translation','culturally-direct','language-help',
        'multiple-acts','authority-professor','process-what-click','provocation',
        'personal-insult','wrong-file-right-content','accidental-fragment'
    }
    assert required <= ids


def test_schema_supports_language_process_and_boundary_intents():
    intents = set(CONVERSATION_SCHEMA['properties']['student_intent']['enum'])
    assert {'language_support','ambiguous_expression','authority_claim','process_question','professional_boundary'} <= intents


def test_semantic_prompt_explicitly_protects_international_students():
    engine = ChallengeEngine(ai=type('NoAI', (), {'available': lambda self: False})())
    challenge = Challenge('c','A1','evidence_auditor','t','p','why',[],[],'move')
    prompt = engine._semantic_system_prompt(challenge, {}, default_memory('evidence_auditor'), None, 'Alex Rivera', 'consequence_visible', [])
    low = prompt.lower()
    for phrase in [
        'international and multilingual students',
        'do not equate imperfect english',
        'literal translations',
        'clear plain english',
        'process question',
        'reviewers can miss or misinterpret evidence',
    ]:
        assert phrase in low
