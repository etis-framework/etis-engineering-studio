from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .course_model import get_phase
from ..config import get_settings

TEXT_SUFFIXES = {'.md', '.txt', '.yml', '.yaml', '.json', '.toml', '.ini', '.cfg', '.py', '.js', '.ts', '.java', '.cs', '.go', '.rs', '.html', '.css'}
BASELINE_MARKERS = [
    'replace this', 'replace with', 'team name', 'your team', 'your project', 'todo', 'tbd',
    'starter', 'template', 'example only', 'not yet applicable', 'complete this', 'fill in',
    '[owner]', '[date]', '[team', '<team', '<project', 'placeholder'
]
READY_CLAIM_RE = re.compile(r'\b(ready|complete|completed|done|release[- ]ready|launch[- ]ready|production[- ]ready)\b', re.I)


@lru_cache
def starter_baseline() -> dict:
    path = get_settings().repo_root / 'course-model' / 'starter_baseline.json'
    if not path.exists():
        return {'files': []}
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache
def baseline_lookup() -> dict[str, dict]:
    return {x['path']: x for x in starter_baseline().get('files', [])}


@dataclass
class ArtifactFact:
    path: str
    exists: bool
    sha256: str = ''
    size: int = 0
    provenance: str = 'UNKNOWN'
    quality: str = 'unknown'
    summary: str = ''
    content_excerpt: str = ''
    url: str = ''
    phase_scope: str = 'CURRENT_PHASE'
    scope_reason: str = ''

    def to_dict(self):
        return asdict(self)


@dataclass
class ReviewFinding:
    id: str
    category: str
    title: str
    statement: str
    significance: str
    severity: int
    confidence: str
    provenance: str = 'REVIEW'
    evidence_refs: list[str] | None = None
    suggested_lens: str = 'evidence_auditor'
    phase_relevance: int = 3
    educational_value: int = 3
    positive: bool = False

    @property
    def rank_score(self) -> int:
        return self.severity * 3 + self.phase_relevance * 2 + self.educational_value * 2

    def to_dict(self):
        d = asdict(self)
        d['rank_score'] = self.rank_score
        d['evidence_refs'] = self.evidence_refs or []
        return d


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_provenance(path: str, sha256: str) -> str:
    baseline = baseline_lookup().get(path)
    if not baseline:
        return 'TEAM_ADDED'
    if baseline.get('sha256') == sha256:
        return 'BASELINE'
    return 'TEAM_ADAPTED'


def text_quality(path: str, content: str, provenance: str) -> tuple[str, str]:
    clean = content.strip()
    lower = clean.lower()
    if provenance == 'BASELINE':
        return 'scaffold', 'Unchanged from the official COMP 330 starter-kit baseline.'
    if not clean:
        return 'empty', 'File is empty.'
    marker_hits = [m for m in BASELINE_MARKERS if m in lower]
    if len(clean) < 120:
        return 'thin', 'Very little project-specific evidence is present.'
    if marker_hits:
        return 'partial', f"Project-specific content may still contain scaffold markers: {', '.join(marker_hits[:3])}."
    return 'reviewable', 'Content appears materially adapted; semantic review may still be required.'


def artifact_from_bytes(path: str, data: bytes, url: str = '') -> ArtifactFact:
    digest = sha256_bytes(data)
    provenance = classify_provenance(path, digest)
    text = ''
    try:
        if Path(path).suffix.lower() in TEXT_SUFFIXES or not Path(path).suffix:
            text = data.decode('utf-8', errors='replace')
    except Exception:
        text = ''
    quality, summary = text_quality(path, text, provenance) if text else ('binary', 'Binary or non-text artifact.')

    if text:
        compact = re.sub(r'\s+', ' ', text).strip()
        excerpt = compact if len(compact) <= 1200 else f"{compact[:600]} … {compact[-600:]}"
    else:
        excerpt = ''
    return ArtifactFact(path=path, exists=True, sha256=digest, size=len(data), provenance=provenance, quality=quality, summary=summary, content_excerpt=excerpt, url=url)


def expected_paths_for_phase(phase_id: str) -> list[str]:
    return [x['path'] for x in get_phase(phase_id).get('expected_evidence', []) if not x['path'].startswith('GitHub ')]


def phase_prefixes(phase_id: str) -> list[str]:
    mapping = {
        'A1': ['README.md', 'docs/team/', 'docs/ai/', 'docs/requirements/', 'docs/planning/', 'docs/decisions/'],
        'A2': ['README.md', 'docs/requirements/', 'docs/planning/', 'docs/decisions/', 'docs/ai/'],
        'A3': ['README.md', 'docs/architecture/', 'docs/decisions/', 'docs/reviews/', 'docs/testing/', 'docs/security/', 'docs/planning/'],
        'A4': ['README.md', 'src/', 'tests/', '.github/', 'docs/testing/', 'docs/reviews/', 'docs/ai/', 'docs/planning/', 'docs/architecture/', 'docs/release/'],
        'A5': ['README.md', 'docs/release/', 'docs/testing/', 'docs/quality/', 'docs/ai/', 'docs/planning/', 'test-evidence/', '.github/'],
        'A6': ['README.md', 'docs/release/', 'docs/operations/', 'docs/observability/', 'docs/security/', 'docs/testing/', 'docs/quality/', 'docs/ai/', 'docs/planning/', '.github/'],
    }
    return mapping.get(phase_id, ['README.md', 'docs/'])


def path_in_phase_scope(path: str, phase_id: str) -> bool:
    """Bounded repository discovery scope. Canonical filenames are clues, not requirements."""
    if any(path == p or path.startswith(p) for p in phase_prefixes(phase_id)):
        return True
    if path.startswith('docs/') or path in {'README.md', 'CONTRIBUTING.md'}:
        return True
    if path.startswith('.github/'):
        return True
    if phase_id in {'A4','A5','A6'} and (path.startswith('src/') or path.startswith('tests/') or path.startswith('test-evidence/')):
        return True
    return False


def evidence_phase_scope(path: str, phase_id: str) -> tuple[str, str]:
    if any(path == p or path.startswith(p) for p in phase_prefixes(phase_id)):
        return 'CURRENT_PHASE', f'Relevant to {phase_id} expected evidence or workflow.'
    if path.startswith('docs/') or path.startswith('.github/') or path in {'README.md','CONTRIBUTING.md'}:
        return 'PROJECT_SPECIFIC', 'Repository-discovered evidence that may support or contradict the active question.'
    return 'OUT_OF_SCOPE', 'Present in the repository but not normally evaluated at this phase.'


def summarize_strengths(phase_id: str, artifacts: list[ArtifactFact], metrics: dict) -> list[str]:
    strengths: list[str] = []
    adapted = [a for a in artifacts if a.provenance in {'TEAM_ADAPTED', 'TEAM_ADDED'} and a.quality == 'reviewable']
    if adapted:
        sample = ', '.join(a.path for a in adapted[:3])
        strengths.append(f"Project-specific evidence is visible in {sample}{' and other artifacts' if len(adapted) > 3 else ''}.")
    baseline = [a for a in artifacts if a.provenance == 'BASELINE']
    if baseline:
        strengths.append('The official COMP 330 engineering scaffold is present, giving the team a consistent evidence structure to build from.')
    if metrics.get('issue_count', 0) > 0:
        strengths.append(f"GitHub shows {metrics['issue_count']} issue record(s), providing visible intent and ownership signals.")
    if phase_id in {'A4', 'A5', 'A6'} and metrics.get('pr_count', 0) > 0:
        strengths.append(f"GitHub shows {metrics['pr_count']} pull request(s), so review and integration behavior can be inspected.")
    if metrics.get('actions_runs', 0) > 0:
        strengths.append(f"GitHub Actions has {metrics['actions_runs']} recent workflow run(s), providing inspectable automation evidence.")
    return strengths[:4]


def _find_artifact(artifacts: list[ArtifactFact], path: str) -> ArtifactFact | None:
    exact = next((a for a in artifacts if a.path == path), None)
    if exact:
        return exact
    path = path.rstrip('/') + '/'
    children = [a for a in artifacts if a.path.startswith(path)]
    if not children:
        return None
    # Directory-level evidence is baseline only when all visible children are baseline.
    prov = 'BASELINE' if all(a.provenance == 'BASELINE' for a in children) else 'TEAM_ADAPTED'
    quality = 'scaffold' if prov == 'BASELINE' else ('reviewable' if any(a.quality == 'reviewable' for a in children) else 'partial')
    return ArtifactFact(path=path, exists=True, provenance=prov, quality=quality, summary=f'{len(children)} artifact(s) visible under this evidence area.')


def build_findings(phase_id: str, artifacts: list[ArtifactFact], metrics: dict, expected_evidence: list[dict]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    refs = {a.path: f'PATH:{a.path}' for a in artifacts}

    # Expected evidence: distinguish absence from unchanged scaffold.
    for idx, exp in enumerate(expected_evidence, 1):
        path = exp['path']
        if path == 'GitHub Issues':
            if metrics.get('issue_count', 0) == 0:
                findings.append(ReviewFinding(f'workflow-issues-{phase_id}', 'workflow_gap', 'No visible issue-based work', 'No GitHub Issues were visible in the reviewed repository state.', 'The course workflow expects meaningful work to have visible intent, ownership, and completion evidence.', 3 if phase_id in {'A2','A3','A4','A5','A6'} else 2, 'high', evidence_refs=['GITHUB:issues'], suggested_lens='delivery'))
            continue
        if path == 'GitHub Pull Requests':
            if metrics.get('pr_count', 0) == 0:
                findings.append(ReviewFinding(f'workflow-prs-{phase_id}', 'workflow_gap', 'No visible pull-request review history', 'No pull requests were visible in the reviewed repository state.', 'Later phase claims about controlled implementation and review need repository-visible review behavior.', 4 if phase_id in {'A4','A5','A6'} else 2, 'high', evidence_refs=['GITHUB:pulls'], suggested_lens='evidence_auditor'))
            continue
        art = _find_artifact(artifacts, path)
        if not art:
            findings.append(ReviewFinding(f'missing-{idx}', 'missing_evidence', f'Expected evidence not visible: {path}', f'The snapshot did not contain `{path}` or an equivalent artifact detected in that evidence area.', exp['claim'], 4, 'high', evidence_refs=[f'PATH:{path}'], suggested_lens='evidence_auditor'))
        elif art.provenance == 'BASELINE':
            findings.append(ReviewFinding(f'baseline-{idx}', 'artifact_theater', f'Scaffold is present but not yet team evidence: {path}', f'`{path}` is unchanged from the official COMP 330 starter-kit baseline.', 'Starter-kit scaffolding is course infrastructure. Its presence does not prove that the team performed, adopted, reviewed, or agreed to the engineering practice.', 3, 'high', evidence_refs=[f'PATH:{path}'], suggested_lens='evidence_auditor'))
        elif art.quality in {'empty', 'thin', 'partial'}:
            findings.append(ReviewFinding(f'weak-{idx}', 'weak_evidence', f'Evidence may be too thin: {path}', f'`{path}` exists but appears incomplete or still scaffold-like.', exp['claim'], 3, 'moderate', evidence_refs=[f'PATH:{path}'], suggested_lens='evidence_auditor'))

    # A1 still expects the team to demonstrate that the repository workflow can operate.
    # This is a workflow fact, not a repository-folder requirement.
    if phase_id == 'A1' and metrics.get('issue_count', 0) == 0 and not any(f.id == 'workflow-issues-A1' for f in findings):
        findings.append(ReviewFinding(
            'workflow-issues-A1', 'workflow_gap', 'No team issue workflow is visible yet',
            'No GitHub Issues were visible in the reviewed repository state.',
            'A1 launch readiness includes establishing a usable issue → branch → pull request → review workflow; an untouched template cannot prove the team has exercised that control.',
            2, 'high', evidence_refs=['GITHUB:issues'], suggested_lens='delivery', phase_relevance=3, educational_value=4
        ))

    # Contradiction: readiness language while phase evidence is still scaffold/missing.
    readme = next((a for a in artifacts if a.path == 'README.md'), None)
    unresolved = [f for f in findings if f.category in {'missing_evidence','artifact_theater','weak_evidence'} and f.severity >= 3]
    if readme and READY_CLAIM_RE.search(readme.content_excerpt or '') and unresolved:
        findings.append(ReviewFinding('readiness-contradiction', 'contradiction', 'Readiness language may outrun the evidence', 'The README uses readiness/completion language while material phase evidence remains missing, scaffolded, or weak.', 'A reviewer should be able to reconcile the team\'s readiness claim with the actual evidence baseline.', 4, 'moderate', evidence_refs=['PATH:README.md'] + [x.evidence_refs[0] for x in unresolved[:2] if x.evidence_refs], suggested_lens='chief_architect'))

    # CI placeholder is a known course baseline control, not actual CI evidence.
    ci = next((a for a in artifacts if a.path == '.github/workflows/ci.yml'), None)
    if phase_id in {'A4','A5','A6'} and ci and ci.provenance == 'BASELINE':
        findings.append(ReviewFinding('ci-placeholder', 'unsupported_claim', 'Starter CI workflow is not project CI', 'The CI workflow is still identical to the intentionally unconfigured starter-kit workflow.', 'A green or present workflow file is not evidence that the project builds or tests successfully.', 5, 'high', evidence_refs=['PATH:.github/workflows/ci.yml'], suggested_lens='evidence_auditor'))

    # Later-phase release/operations workflow signals.
    if phase_id in {'A5','A6'} and metrics.get('tag_count', 0) == 0:
        findings.append(ReviewFinding('release-baseline-missing', 'release_control', 'No release/tag baseline was visible', 'No repository tag was visible for the reviewed repository.', 'Release claims should point to a stable repository baseline that another reviewer can inspect.', 4, 'high', evidence_refs=['GITHUB:tags'], suggested_lens='chief_architect'))
    if phase_id == 'A6' and metrics.get('actions_runs', 0) == 0:
        findings.append(ReviewFinding('ops-automation-gap', 'operational_gap', 'No recent automation runs were visible', 'No recent GitHub Actions runs were visible in the repository evidence gathered for the final maturity review.', 'Operational and release maturity should include inspectable automation or a documented reason why automation is not applicable.', 3, 'moderate', evidence_refs=['GITHUB:actions'], suggested_lens='delivery'))

    findings.sort(key=lambda f: (f.rank_score, f.severity), reverse=True)
    return findings


def rank_challenges(findings: list[ReviewFinding], prior_categories: Iterable[str] | None = None, limit: int = 4) -> list[ReviewFinding]:
    prior = set(prior_categories or [])
    ranked = sorted(findings, key=lambda f: (f.rank_score - (5 if f.category in prior else 0), f.severity), reverse=True)
    selected: list[ReviewFinding] = []
    categories: set[str] = set()
    for f in ranked:
        # Prefer diversity before repeating the same review theme.
        if f.category in categories and len(selected) < min(2, limit):
            continue
        selected.append(f)
        categories.add(f.category)
        if len(selected) >= limit:
            break
    return selected


def analyze_local_repository(root: Path, phase_id: str, metrics: dict | None = None) -> dict:
    metrics = {**{'issue_count': 0, 'pr_count': 0, 'actions_runs': 0, 'tag_count': 0, 'commit_count': 0}, **(metrics or {})}
    artifacts: list[ArtifactFact] = []
    for p in root.rglob('*'):
        if not p.is_file() or '.git' in p.parts:
            continue
        rel = p.relative_to(root).as_posix()
        if not path_in_phase_scope(rel, phase_id):
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        artifacts.append(artifact_from_bytes(rel, data))
    phase = get_phase(phase_id)
    findings = build_findings(phase_id, artifacts, metrics, phase['expected_evidence'])
    return {
        'artifacts': [a.to_dict() for a in artifacts],
        'metrics': metrics,
        'strengths': summarize_strengths(phase_id, artifacts, metrics),
        'findings': [f.to_dict() for f in findings],
        'challenges': [f.to_dict() for f in rank_challenges(findings)],
    }
