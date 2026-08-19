from pathlib import Path

from apps.api.app.services.ai_telemetry import estimate_cost, merge_usage, RATE_CARD_VERSION
from apps.api.app.services.evidence_package import EvidencePackageBuilder
from apps.api.app.services.challenge_engine import ChallengeEngine, Challenge, default_memory
from apps.api.app.services.ai_provider import CONVERSATION_SCHEMA


def test_cost_estimate_accounts_for_cached_input():
    uncached = estimate_cost('gpt-5.6', 10_000, 0, 1_000)
    cached = estimate_cost('gpt-5.6', 10_000, 8_000, 1_000)
    assert cached < uncached
    assert RATE_CARD_VERSION.startswith('openai-public-')


def test_usage_merge_keeps_calls_and_cost():
    out = merge_usage([
        {'input_tokens': 100, 'cached_input_tokens': 25, 'output_tokens': 20, 'latency_ms': 400, 'estimated_cost_usd': .001, 'purpose': 'a'},
        {'input_tokens': 200, 'cached_input_tokens': 50, 'output_tokens': 30, 'latency_ms': 600, 'estimated_cost_usd': .002, 'purpose': 'b'},
    ])
    assert out['calls'] == 2
    assert out['input_tokens'] == 300
    assert out['cached_input_tokens'] == 75
    assert out['estimated_cost_usd'] == .003


def test_compact_evidence_package_does_not_ship_entire_repo():
    evidence = {
        'phase_id': 'A1', 'repo_full_name': 'x/y', 'commit_sha': 'abc',
        'strengths': ['roles visible'],
        'items': [{'ref': 'EV-1', 'status': 'present', 'title': 'docs/team/roles.md', 'detail': 'roles', 'provenance': 'FACT', 'source_provenance': 'TEAM_ADAPTED', 'quality': 'reviewable'}],
        'artifacts': [
            {'path': 'docs/team/roles.md', 'provenance': 'TEAM_ADAPTED', 'quality': 'reviewable', 'summary': 'roles', 'content_excerpt': 'A'*4000},
            {'path': 'docs/requirements/requirements.md', 'provenance': 'TEAM_ADAPTED', 'quality': 'reviewable', 'summary': 'reqs', 'content_excerpt': 'B'*4000},
        ],
        'repository_metrics': {'issue_count': 2, 'issues': [{'number': 1, 'title': 'Launch'}]},
        'longitudinal': {},
    }
    challenge = {'title': 'Ownership', 'evidence_refs': ['PATH:docs/team/roles.md'], 'finding': {'category': 'ownership_ambiguity'}, 'decision_question': 'Who owns it?', 'why_now': 'A1'}
    pkg = EvidencePackageBuilder().build(evidence, challenge)
    text = pkg.to_prompt_text()
    assert 'docs/team/roles.md' in text
    assert 'docs/requirements/requirements.md' not in text
    assert len(text) < 14000


def test_conversation_schema_has_outlier_intents():
    values = CONVERSATION_SCHEMA['properties']['student_intent']['enum']
    for expected in ['humor', 'rambling', 'self_correction', 'misconception', 'source_request', 'example_request', 'disengaged']:
        assert expected in values


def test_semantic_prompt_explicitly_handles_combative_and_poor_language():
    engine = ChallengeEngine(ai=type('NoAI', (), {'available': lambda self: False})())
    challenge = Challenge('c','A1','evidence_auditor','t','p','why',[],[],'move')
    prompt = engine._semantic_system_prompt(challenge, {}, default_memory('evidence_auditor'), None, 'Alex Rivera', 'consequence_visible', [])
    assert 'combative' in prompt.lower()
    assert 'slang' in prompt.lower()
    assert 'secret phrase' in prompt.lower()
    assert 'ramble' in prompt.lower()
