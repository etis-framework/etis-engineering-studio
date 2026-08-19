from __future__ import annotations

import json
from dataclasses import dataclass

from .ai_provider import OpenAIResponsesProvider
from .course_model import get_phase
from .model_disclosure import sanitize_model_artifact


@dataclass
class SemanticAssessment:
    strengths: list[str]
    findings: list[dict]
    equivalent_evidence: list[dict]
    usage_events: list[dict]


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
        visible_paths = {a.get('path') for a in artifacts if a.get('path')}
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

            artifact_context.append({
                'path': a.get('path'),
                'provenance': a.get('provenance'),
                'quality': a.get('quality'),
                'summary': a.get('summary'),
                'excerpt': disclosure.text,
                'disclosure_status': disclosure_status,
                'disclosure_reasons': list(disclosure.redactions),
            })
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
- Only cite evidence_paths that appear in the supplied artifact list. If no supplied evidence supports a statement, do not cite a path.
- Equivalent evidence is allowed: if the expected concept is credibly addressed in another supplied artifact, identify it rather than insisting on one filename.
- Keep strengths factual and specific. Do not praise template structure as if it were team-authored work.

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
{json.dumps(artifact_context)[:28000]}

Identify no more than 4 strong positive observations and 6 high-value REVIEW findings. Avoid duplicating obvious exact-path findings unless semantic interpretation materially adds something.
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
        return SemanticAssessment(strengths, findings, equivalent, [raw.get("_usage")] if raw.get("_usage") else [])
