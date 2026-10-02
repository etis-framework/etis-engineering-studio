from pathlib import Path

from apps.api.app.routers.reviews import _infer_finding_id
from apps.api.app.services.guidance import guidance_for_topic
from apps.api.app.services.repository_intelligence import artifact_from_bytes, classify_provenance

FIXTURES = Path('tests/fixtures/starter_subset')


def test_line_ending_and_bom_normalization_do_not_create_team_authorship():
    path = 'docs/ai/ai-use-log.md'
    original = (FIXTURES / path).read_bytes()
    crlf = b'\xef\xbb\xbf' + original.replace(b'\n', b'\r\n')
    art = artifact_from_bytes(path, crlf)
    assert art.provenance == 'BASELINE'
    assert art.quality == 'scaffold'


def test_starter_like_version_drift_is_not_promoted_to_team_adapted():
    path = 'docs/planning/risk-register.md'
    original = (FIXTURES / path).read_text(encoding='utf-8')
    # Simulate a refreshed official starter copy: a generic scaffold-only note,
    # no project-specific risk record.
    drifted = (original + '\n<!-- starter-kit wording refresh -->\n').encode()
    art = artifact_from_bytes(path, drifted)
    assert art.provenance == 'STARTER_DERIVED'
    assert art.quality == 'scaffold'
    assert 'Starter-derived scaffold' in art.summary


def snapshot_findings():
    return {
        'findings': [
            {'id': 'arch', 'category': 'architecture', 'title': 'Architecture package substantively empty',
             'statement': 'Project-specific components, interfaces and dependency direction are not demonstrated.',
             'significance': 'Architecture boundaries remain unclear.'},
            {'id': 'ai', 'category': 'ai_governance', 'title': 'AI-use disclosure is only an empty log',
             'statement': 'AI use or non-use and human verification are not demonstrated.',
             'significance': 'AI disclosure and verification remain unknown.'},
            {'id': 'risk', 'category': 'risk', 'title': 'Consequential risks remain unmanaged',
             'statement': 'Risk likelihood, impact, mitigation, owner and reassessment are not demonstrated.',
             'significance': 'Project risk remains unbounded.'},
            {'id': 'decision', 'category': 'decision', 'title': 'Architecture decisions are not traceable',
             'statement': 'No ADR or accepted design decision with alternatives and consequences is demonstrated.',
             'significance': 'Tradeoffs cannot be reviewed.'},
        ],
        'challenge_candidates': [],
    }


def test_topic_jumps_resolve_to_unique_frozen_finding_and_pronouns_do_not_invent_switches():
    ev = snapshot_findings()
    assert _infer_finding_id(ev, 'Search for our AI use or non-use disclosure and human verification.') == 'ai'
    assert _infer_finding_id(ev, 'Find where we managed risk, likelihood, impact, mitigation and reassessment.') == 'risk'
    assert _infer_finding_id(ev, 'We recorded an ADR decision with alternatives and consequences somewhere.') == 'decision'
    assert _infer_finding_id(ev, 'Search for architecture components, interfaces and dependency direction.') == 'arch'
    assert _infer_finding_id(ev, 'I know we did this somewhere. Find it.') is None
    assert _infer_finding_id(ev, 'Does this resolve it?') is None


def test_unrelated_a3_architecture_guidance_is_not_used_for_ai_or_risk_topic():
    assert guidance_for_topic('A3', 'We may have documented AI use or non-use somewhere else.', limit=2) == []
    refs = guidance_for_topic('A2', 'Search for project risk mitigation likelihood impact and reassessment.', limit=2)
    assert all('architecture' not in (str(r.get('title') or '') + str(r.get('summary') or '')).lower() for r in refs)


def test_a1_a6_topic_jump_wargame_matrix_preserves_explicit_topic_and_ambiguous_followup():
    phases = ('A1','A2','A3','A4','A5','A6')
    repo_strengths = ('weak','average','strong')
    students = ('weak','average','strong')
    ev = snapshot_findings()
    prompts = {
        'weak': 'risk somewhere find it mitigation owner',
        'average': 'Search the repository for evidence of risk likelihood impact mitigation owner and reassessment.',
        'strong': 'Locate equivalent frozen evidence demonstrating risk ownership, mitigation, status, and reassessment; reject templates.',
    }
    count = 0
    for phase in phases:
        for repo_strength in repo_strengths:
            for student in students:
                assert _infer_finding_id(ev, prompts[student]) == 'risk'
                # After a strong explicit switch, a pronoun-only follow-up must not
                # manufacture a different finding; persisted active state owns it.
                assert _infer_finding_id(ev, 'What does this actually prove?') is None
                assert phase and repo_strength
                count += 1
    assert count == 54


def test_student_modified_starter_with_substantive_change_remains_team_adapted():
    path = 'docs/ai/ai-use-log.md'
    original = (FIXTURES / path).read_text(encoding='utf-8')
    changed = (original + '\n2026-10-01 | architecture.md | Copilot generated design | Maya | reviewed interface contract | accepted\n').encode()
    art = artifact_from_bytes(path, changed)
    assert art.provenance == 'TEAM_ADAPTED'
