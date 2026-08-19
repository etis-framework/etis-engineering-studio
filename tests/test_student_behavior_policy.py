import json
from pathlib import Path
from apps.api.app.services.ai_provider import CONVERSATION_SCHEMA
from apps.api.app.services.challenge_engine import ChallengeEngine, Challenge, default_memory


def test_behavior_regression_corpus_is_broad():
    rows = json.loads(Path('evals/student_behavior_cases.json').read_text())
    assert len(rows) >= 30
    ids = {x['id'] for x in rows}
    for needed in {'tentative-correct','combative','non-native-english','grading-game','evidence-dispute','stuck','answer-seeking','misconception-ci'}:
        assert needed in ids


def test_schema_supports_mature_conversation_intents():
    intents = set(CONVERSATION_SCHEMA['properties']['student_intent']['enum'])
    for intent in {'simplify_request','grading_request','skip_request','hostility','frustration','meta_repair','evidence_dispute'}:
        assert intent in intents


def test_prompt_covers_novice_and_adversarial_interaction_policy():
    engine = ChallengeEngine(ai=type('NoAI', (), {'available': lambda self: False})())
    challenge = Challenge('c','A1','evidence_auditor','t','p','why',[],[],'move')
    prompt = engine._semantic_system_prompt(challenge, {}, default_memory('evidence_auditor'), None, 'Alex Rivera', 'consequence_visible', [])
    lower = prompt.lower()
    for phrase in ['combative','secret phrase','non-expert','simplify','full points','skip','hostile','polished answer','senior engineer\'s perspective']:
        assert phrase in lower
