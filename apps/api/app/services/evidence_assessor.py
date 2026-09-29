from __future__ import annotations

import json
import re
from dataclasses import dataclass
from dataclasses import field

from .ai_provider import OpenAIResponsesProvider
from .course_model import get_phase
from .model_disclosure import sanitize_model_artifact


@dataclass
class SemanticAssessment:
    strengths: list[str]
    findings: list[dict]
    equivalent_evidence: list[dict]
    usage_events: list[dict]
    claim_support: list[dict] = field(default_factory=list)


def _normalized_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip().casefold()


_UNFILLED_EVIDENCE = re.compile(r'\b(?:TODO|TBD|placeholder|fill in|example only)\b', re.I)
_DESIGN_ONLY_LANGUAGE = re.compile(r'\b(?:will|should|must|planned|proposed|template)\b', re.I)
_HUMAN_CHECK_ACTION = re.compile(
    r'\b(?:checked|verified|compared|reviewed|accepted|rejected|changed|retained|'
    r'validated|corrected|examined|assessed|cross-checked|confirmed|tested)\b', re.I)
_NON_OPERATING_EXAMPLE = re.compile(
    r'\b(?:example|sample|illustrative|hypothetical)\b|\bno AI (?:assistance|use)\b|\bAI was not used\b', re.I)

# These phase claims describe a control operating, rather than a control's
# existence. A policy or blank log cannot establish that the team used it.
_OPERATING_RECORD_CLAIMS = {'docs/ai/ai-use-log.md'}


class SemanticEvidenceAssessor:
    """Adds semantic REVIEW interpretation without changing deterministic FACTS.

    This layer can notice weak content, contradictions, alternate/equivalent evidence,
    traceability problems, or tradeoffs that exact-path checks cannot understand. Every
    returned evidence reference is validated against the frozen snapshot before use.
    """

    def __init__(self, ai=None):
        self.ai = ai or OpenAIResponsesProvider()

    def available(self) -> bool:
        return self.ai.available()

    def assess(self, phase_id: str, repo_full_name: str, commit_sha: str, artifacts: list[dict], metrics: dict) -> SemanticAssessment:
        if not self.available():
            return SemanticAssessment([], [], [], [])
        phase = get_phase(phase_id)
        artifact_context = []
        for a in artifacts:
            disclosure = sanitize_model_artifact(
                a.get('path'),
                (a.get('content_excerpt') or '')[:1200],
            )
            if 'sensitive_file' in disclosure.redactions:
                disclosure_status = 'quarantined'
            elif disclosure.redactions:
                disclosure_status = 'redacted'
            else:
                disclosure_status = 'clear'

            operating_excerpt = ''
            if a.get('path') in _OPERATING_RECORD_CLAIMS:
                retained = a.get('content_excerpt') or ''
                if len(retained) > 1200:
                    later = sanitize_model_artifact(a.get('path'), retained[-1200:])
                    if later.redactions:
                        disclosure_status = 'redacted'
                    else:
                        operating_excerpt = later.text
            artifact_context.append({
                'path': a.get('path'),
                'provenance': a.get('provenance'),
                'quality': a.get('quality'),
                'summary': a.get('summary'),
                'excerpt': disclosure.text,
                'operating_excerpt': operating_excerpt,
                'disclosure_status': disclosure_status,
                'disclosure_reasons': list(disclosure.redactions),
            })
        expected_paths = [x.get('path', '') for x in phase.get('expected_evidence', [])]
        artifact_context.sort(key=lambda a: (
            0 if a['path'] in expected_paths else
            1 if any(p.endswith('/') and a['path'].startswith(p) for p in expected_paths) else 2
        ))
        # Supply complete JSON records, not an arbitrarily truncated JSON string.
        # Validate model citations against exactly the records the model saw.
        supplied_context = []
        for artifact in artifact_context:
            if len(json.dumps([*supplied_context, artifact])) > 28000:
                break
            supplied_context.append(artifact)
        visible_paths = {a['path'] for a in supplied_context}
        system = f"""
You are the semantic evidence assessor for the ETIS Engineering Studio. You are NOT the conversational reviewer.
Analyze only the supplied frozen repository evidence for COMP 330 phase {phase_id}.

AUTHORITY RULES
- Repository/file/GitHub observations are FACTS supplied by the application. Never invent files, content, workflow history, tests, approvals, or student actions.
- Your output is REVIEW interpretation. It may identify meaning, weak claims, contradictions, alternate evidence, or consequential tradeoffs.
- Do not punish a team for later-lifecycle evidence that is not appropriate to {phase_id}.
- A file inherited unchanged from the COMP 330 starter kit is scaffold, not proof that the team performed the practice.
- A materially adapted file may still be weak; judge whether the supplied excerpt supports the phase claim.
- Prefer substantive engineering findings over cosmetic documentation observations.
- Strong repositories still deserve engineering-tradeoff questions when there is no material defect.
- Reason ACROSS artifacts, not just within files. Surface material contradictions, status mismatches, and places where one artifact assumes a decision another still marks proposed/open.
- Treat consequential assumptions and uncertainty as first-class evidence. An estimate, architecture choice, verification claim, or operational promise may be defensible only if its assumptions are visible and bounded.
- When artifacts conflict, ask whether the repository establishes an authoritative source of truth or supersession relationship. Do not arbitrarily choose a winner.
- Distinguish a control being DEFINED, DEMONSTRATED, CONSISTENTLY APPLIED, and EFFECTIVE. A written policy alone does not prove the control operated.
- Calibrate claim strength to evidence. Flag material cases where a team claim (for example complete, accepted, verified, release-ready, production-ready) is stronger than the supplied evidence.
- Distinguish mechanisms from demonstrated outcomes: backup is not restore evidence; logging is not demonstrated observability; CI presence is not proof of meaningful verification; a runbook is not proof of recoverability.
- Distinguish current course phase-gate readiness concerns from broader professional engineering challenges when possible; do not imply every professional observation is a course requirement.
- Studio is used DURING preparation. Absence of a phase-gate submission tag is not itself a defect. A required tag should identify the exact intended submission commit only when the package is submitted for final instructor review.
- Only cite evidence_paths that appear in the supplied artifact list. If no supplied evidence supports a statement, do not cite a path.
- Equivalent evidence is allowed: if the expected concept is credibly addressed in another supplied artifact, identify it rather than insisting on one filename.
- Keep strengths factual and specific. Do not praise template structure as if it were team-authored work.
- For up to four expected phase claims, return affirmative claim_support only when a specific supplied excerpt supports it. Quote an exact continuous span from one team-authored artifact. The quote must demonstrate the stated claim rather than repeat a heading, template instruction, or aspiration. Use the expected_path exactly as listed and a supplied support_path. Describe the bounded claim, not the quality of an entire file.
- Strong requires a demonstrated team decision or behavior, high confidence, and no material contradiction in supplied evidence. A defined policy without an operating example, counts of issues/PRs, or a polished plan without actual decisions is at most Okay. If context is missing, truncated, or conflicting, omit the positive claim rather than guess. State a meaningful limitation and next step even for Strong; never imply phase-gate approval or a grade.
- For an AI-use-log claim, a policy, blank table, or intended verification process is not affirmative support. If material AI use was recorded, cite a filled operating record that names what was used and what a human checked or changed. Supply operating_evidence_path and an exact continuous operating_evidence_quote from a team-authored excerpt or operating_excerpt; otherwise omit the claim. These are bounded windows, not the whole file. An explicit no-use statement may be useful context but does not prove that AI-assisted work was logged and reviewed. For other claims use empty strings when no separate operating record is necessary. Do not infer that no AI was used from an empty log.
- In A2, a populated requirement-to-task row can support a defined trace, and an estimate with a real range and assumption can support that bounded decision. Do not claim a task was completed, reviewed, or verified from a plan alone. GitHub counts are discovery clues; tie actual work to an identified requirement and outcome before interpreting follow-through. Treat a missing visible issue as an uncertainty to check if the team supplies another credible work record.

PHASE PURPOSE
{phase.get('purpose','')}

EXPECTED EVIDENCE
{json.dumps(phase.get('expected_evidence', []), indent=2)}

DECISIONS TO DEFEND
{json.dumps(phase.get('decisions_to_defend', []), indent=2)}
""".strip()
        user = f"""
Repository: {repo_full_name}
Frozen commit: {commit_sha}
GitHub metrics: {json.dumps(metrics)}
Artifacts and bounded excerpts:
{json.dumps(supplied_context)}

Identify no more than 4 positive claim supports and 6 high-value REVIEW findings. Avoid duplicating obvious exact-path findings unless semantic interpretation materially adds something. Return an empty claim_support array when the bounded excerpts do not substantiate a positive phase claim.
For every finding, classify review_scope as course_readiness, professional_challenge, or both, and identify the dominant reasoning_pattern. A professional_challenge may teach industry judgment without implying that the course phase requires remediation.
""".strip()
        raw = self.ai.repository_assessment(system, user)

        strengths = [str(x).strip() for x in raw.get('strengths', []) if str(x).strip()][:4]
        findings: list[dict] = []
        seen = set()
        for idx, f in enumerate(raw.get('findings', [])[:6], 1):
            refs = [p for p in f.get('evidence_paths', []) if p in visible_paths]
            key = (f.get('category'), f.get('title'))
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                'id': f'semantic-{idx}',
                'category': f.get('category', 'weak_evidence'),
                'title': str(f.get('title', '')).strip() or 'Semantic evidence review',
                'statement': str(f.get('statement', '')).strip(),
                'significance': str(f.get('significance', '')).strip(),
                'severity': int(f.get('severity', 2)),
                'confidence': f.get('confidence', 'moderate'),
                'provenance': 'REVIEW',
                'evidence_refs': [f'PATH:{p}' for p in refs],
                'suggested_lens': f.get('suggested_lens', 'evidence_auditor'),
                'phase_relevance': 4,
                'educational_value': 4,
                'positive': False,
                'rank_score': int(f.get('severity', 2)) * 3 + 16,
                'semantic': True,
                'review_scope': f.get('review_scope', 'both'),
                'reasoning_pattern': f.get('reasoning_pattern', 'other'),
            })

        equivalent: list[dict] = []
        expected_paths = {x.get('path') for x in phase.get('expected_evidence', [])}
        for e in raw.get('equivalent_evidence', [])[:8]:
            if e.get('actual_path') not in visible_paths or e.get('expected_path') not in expected_paths:
                continue
            equivalent.append({
                'expected_path': e.get('expected_path'),
                'actual_path': e.get('actual_path'),
                'explanation': str(e.get('explanation', '')).strip(),
                'confidence': e.get('confidence', 'moderate'),
                'provenance': 'REVIEW',
            })
        expected_claims = {
            x.get('path'): x.get('claim', '')
            for x in phase.get('expected_evidence', [])
            if x.get('path') and not x['path'].startswith('GitHub ')
        }
        by_path = {a['path']: a for a in supplied_context if a.get('path')}
        raw_artifacts = {a['path']: a for a in artifacts if a.get('path')}
        support: list[dict] = []
        seen_claims: set[str] = set()
        for candidate in raw.get('claim_support', [])[:4]:
            if not isinstance(candidate, dict):
                continue
            expected = candidate.get('expected_path')
            path = candidate.get('support_path')
            source = by_path.get(path)
            fact = raw_artifacts.get(path)
            quote = str(candidate.get('support_quote') or '').strip()
            kind = candidate.get('support_kind')
            judgment = candidate.get('judgment')
            confidence = candidate.get('confidence')
            rationale = str(candidate.get('rationale') or '').strip()[:350]
            limitation = str(candidate.get('limitation') or '').strip()[:240]
            next_step = str(candidate.get('next_step') or '').strip()[:240]
            operating_path = str(candidate.get('operating_evidence_path') or '').strip()
            operating_quote = str(candidate.get('operating_evidence_quote') or '').strip()
            if (expected not in expected_claims or expected in seen_claims or not source or not fact
                or fact.get('provenance') not in {'TEAM_ADDED', 'TEAM_ADAPTED'}
                or fact.get('quality') != 'reviewable' or source['disclosure_status'] != 'clear'
                or len(quote) < 24 or len(quote) > 300
                or _UNFILLED_EVIDENCE.search(quote)
                or (kind == 'demonstrated' and _DESIGN_ONLY_LANGUAGE.search(quote))
                or not any(_normalized_text(quote) in _normalized_text(window)
                           for window in (source['excerpt'], source['operating_excerpt']))
                or kind not in {'defined', 'demonstrated'}
                or judgment not in {'strong', 'okay'} or confidence not in {'moderate', 'high'}
                or not rationale or not limitation or not next_step):
                continue
            if expected in _OPERATING_RECORD_CLAIMS:
                operating_source = by_path.get(operating_path)
                operating_fact = raw_artifacts.get(operating_path)
                if (kind != 'demonstrated' or not operating_source or not operating_fact
                    or operating_fact.get('provenance') not in {'TEAM_ADDED', 'TEAM_ADAPTED'}
                    or operating_fact.get('quality') != 'reviewable'
                    or operating_source['disclosure_status'] != 'clear'
                    or len(operating_quote) < 24 or len(operating_quote) > 300
                    or _UNFILLED_EVIDENCE.search(operating_quote)
                    or _NON_OPERATING_EXAMPLE.search(operating_quote)
                    or not _HUMAN_CHECK_ACTION.search(operating_quote)
                    or not any(_normalized_text(operating_quote) in _normalized_text(window)
                               for window in (operating_source['excerpt'], operating_source['operating_excerpt']))):
                    continue
            # A short excerpt can substantiate a bounded claim, not whole-file quality.
            # A long artifact's decisive section may be beyond the retained 8000 chars.
            if judgment == 'strong' and (kind != 'demonstrated' or confidence != 'high'
                                         or int(fact.get('size') or 0) > 8000):
                judgment = 'okay'
            support.append({
                'expected_path': expected, 'claim': expected_claims[expected],
                'support_path': path, 'support_quote': quote,
                'support_kind': kind, 'judgment': judgment, 'confidence': confidence,
                'rationale': rationale, 'limitation': limitation, 'next_step': next_step,
                'provenance': 'REVIEW', 'inspection_scope': 'bounded_excerpt',
                'operating_evidence_path': operating_path if expected in _OPERATING_RECORD_CLAIMS else '',
                'operating_evidence_quote': operating_quote if expected in _OPERATING_RECORD_CLAIMS else '',
            })
            seen_claims.add(expected)
        return SemanticAssessment(strengths, findings, equivalent,
                                  [raw.get("_usage")] if raw.get("_usage") else [], support)
