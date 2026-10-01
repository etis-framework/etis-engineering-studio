"""Bounded earlier-phase coaching from artifacts in the current frozen snapshot."""

import re

from .repository_intelligence import ReviewFinding


PHASES = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6')
# Signals are deliberately broad: an equivalent file under docs/ can satisfy a
# signal. A filename alone never establishes that a practice was performed.
FOUNDATIONS = {
    'A1': (('launch direction', r'readme|scope|stakeholder|project.charter|requirements'),
           ('team ownership', r'team.charter|roles|working.agreement|decision')),
    'A2': (('requirements and planning', r'requirement|scope|traceab|task.plan|estimate|schedule'),
           ('risk and adjustment', r'risk|re.estimat|dependenc')),
    'A3': (('architecture boundaries', r'architect|component|responsib|interface|api.contract'),
           ('architecture decisions', r'data.context|decision|design.review')),
    'A4': (('implementation', r'(^src/|/src/|implementation|construction)'),
           ('verification', r'(^tests/|/tests/|testing|test.evidence|\.github/workflows/)')),
    'A5': (('acceptance and verification', r'acceptance|test.evidence|quality|testing'),
           ('release control', r'release|deployment|runbook')),
}


def coaching_phase(current_phase: str, student_text: str, previous: str | None = None) -> str:
    """Honor an explicit earlier phase; keep follow-up questions on that topic."""
    allowed = PHASES[:PHASES.index(current_phase) + 1] if current_phase in PHASES else (current_phase,)
    mentioned = re.findall(r'\bA[1-6]\b', student_text, flags=re.I)
    if mentioned:
        chosen = mentioned[-1].upper()
        return chosen if chosen in allowed else current_phase
    topic_patterns = (
        ('A1', r'project launch|launch gate|stakeholder|team.charter|working.agreement|team/roles'),
        ('A2', r're.estimat|work breakdown|planning gate|cycle 1 plan'),
        ('A3', r'architecture|component boundar|system design'),
        ('A4', r'implementation review|code review|integration test'),
        ('A5', r'release gate|release baseline|acceptance test'),
    )
    matches = [phase for phase, pattern in topic_patterns
               if phase in allowed and re.search(pattern, student_text, re.I)]
    if len(matches) == 1:
        return matches[0]
    return previous if previous in allowed else current_phase


def turn_coaching_phase(current_phase: str, student_text: str, previous: str | None,
                       evidence_refs=()) -> str:
    """Apply the same topic resolution to prompt construction and evidence retrieval."""
    topic = coaching_phase(current_phase, student_text, previous)
    if evidence_refs and not re.search(r'\bA[1-6]\b', student_text, re.I):
        topic = coaching_phase(current_phase, ' '.join(map(str, evidence_refs)), topic)
    return topic


def foundation_concern(phase_id: str, artifacts: list[dict]) -> ReviewFinding | None:
    """Surface one observed upstream gap; never infer a complete phase from presence."""
    if phase_id not in PHASES[1:]:
        return None
    for earlier in PHASES[:PHASES.index(phase_id)]:
        signals = FOUNDATIONS.get(earlier)
        if not signals:
            continue
        weak = []
        strong = []
        uncertain = []
        for label, pattern in signals:
            relevant = [a for a in artifacts if re.search(pattern, a.get('path', ''), re.I)]
            inspected = [a for a in relevant if a.get('quality') not in {'uninspected', 'too_large', 'unknown'}]
            if not inspected and relevant:
                uncertain.append(label)
            elif any(a.get('provenance') in {'TEAM_ADAPTED', 'TEAM_ADDED'}
                     and a.get('quality') in {'reviewable', 'partial'} for a in inspected):
                strong.append(label)
            else:
                weak.append((label, relevant))
        if not weak or strong or uncertain:
            continue
        observed = [a['path'] for _, group in weak for a in group]
        # Do not promote absence of a canonical path: discovery may be bounded.
        if not observed:
            continue
        names = ', '.join(label for label, _ in weak)
        refs = [f'PATH:{path}' for path in observed[:4]]
        return ReviewFinding(
            id=f'foundation-{earlier}-for-{phase_id}', category='foundation_gap',
            title=f'{earlier} foundation needs checking before {phase_id} claims',
            statement=(f'In this frozen {phase_id} snapshot, the inspected {earlier} {names} '
                       f'evidence is still starter scaffold or thin; examples: {", ".join(observed[:4])}. '
                       'This is an interpretation of inspected sources, not proof that equivalent team work does not exist.'),
            significance=(f'{phase_id} decisions depend on earlier project foundations. '
                          'First identify a team-authored equivalent in this snapshot, or strengthen the earliest '
                          'unsupported decision and record how the team checked it.'),
            severity=4, confidence='moderate', evidence_refs=refs,
            suggested_lens='evidence_auditor', phase_relevance=4, educational_value=4,
        )
    return None
