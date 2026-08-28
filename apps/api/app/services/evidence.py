from __future__ import annotations

import base64
import copy
import time
from dataclasses import dataclass, asdict
from typing import Iterable

import httpx

from ..config import get_settings
from .course_model import get_phase
from .evidence_assessor import SemanticEvidenceAssessor
from .github_app import manager as github_app_manager
from .repository_policy import is_comp330_starter_kit
from .repository_intelligence import (
    ArtifactFact,
    ReviewFinding,
    artifact_from_bytes,
    build_findings,
    path_in_phase_scope,
    rank_challenges,
    summarize_strengths,
    evidence_phase_scope,
)


@dataclass
class EvidenceItem:
    ref: str
    kind: str
    status: str
    title: str
    detail: str
    url: str = ''
    freshness: str = 'unknown'
    provenance: str = 'FACT'
    source_provenance: str = 'UNKNOWN'
    quality: str = 'unknown'
    phase_scope: str = 'CURRENT_PHASE'
    scope_reason: str = ''
    equivalent_path: str = ''


@dataclass
class EvidenceSnapshotData:
    phase_id: str
    repo_full_name: str
    commit_sha: str
    coverage: int
    items: list[EvidenceItem]
    strengths: list[str]
    gaps: list[str]
    warnings: list[str]
    repository_metrics: dict
    artifacts: list[dict]
    findings: list[dict]
    challenge_candidates: list[dict]
    snapshot_kind: str = 'github'
    longitudinal: dict | None = None
    equivalent_evidence: list[dict] | None = None
    semantic_review: dict | None = None
    ai_usage_events: list[dict] | None = None

    def to_dict(self):
        return asdict(self)


def _path_matches(expected: str, actual_paths: set[str]) -> bool:
    expected = expected.strip()
    if expected.startswith('GitHub '):
        return False

    is_directory = expected.endswith('/')
    normalized = expected.strip('/')

    if is_directory:
        prefix = normalized + '/'
        return any(p.startswith(prefix) for p in actual_paths)

    return normalized in actual_paths


class GitHubEvidenceProvider:
    """Phase-aware, read-only GitHub evidence acquisition.

    Public repositories can be inspected without authentication. Private team repositories
    require a GitHub App installation. Personal access tokens are never used.
    """

    def __init__(self, semantic_assessor: SemanticEvidenceAssessor | None = None):
        settings = get_settings()
        self.s = settings
        self.semantic_assessor = semantic_assessor or SemanticEvidenceAssessor()
        self._cache: dict[tuple[str, str], tuple[float, EvidenceSnapshotData]] = {}
        self.base = 'https://api.github.com'
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }

    def _headers_for(self, repo_full_name: str):
        headers=dict(self.headers)

        # The shared starter kit is a known public acceptance fixture. It is
        # intentionally fetched without credentials. Whether it may become a
        # team's authoritative repository is enforced separately by onboarding
        # and is limited to the configured production-test student identity.
        if is_comp330_starter_kit(repo_full_name):
            return headers

        if 'Authorization' not in headers and github_app_manager.configured():
            installation=github_app_manager.token_for_repo(repo_full_name)
            headers['Authorization']=f'Bearer {installation.token}'

        return headers

    def _json_count(self, response, exclude_prs=False):
        if not response.is_success:
            return 0
        data = response.json()
        if not isinstance(data, list):
            return 0
        if exclude_prs:
            data = [x for x in data if 'pull_request' not in x]
        return len(data)

    def _issue_summaries(self, response):
        if not response.is_success or not isinstance(response.json(), list):
            return []
        out = []
        for x in response.json():
            if 'pull_request' in x:
                continue
            out.append({
                'number': x.get('number'), 'title': x.get('title',''), 'state': x.get('state'),
                'assignees': [a.get('login') for a in x.get('assignees', []) if a.get('login')],
                'labels': [l.get('name') for l in x.get('labels', []) if l.get('name')],
                'milestone': (x.get('milestone') or {}).get('title'),
                'created_at': x.get('created_at'), 'closed_at': x.get('closed_at'),
            })
        return out[:25]

    def _pull_summaries(self, response, client=None, repo_full_name='', include_reviews=False):
        if not response.is_success or not isinstance(response.json(), list):
            return []
        out = []
        for x in response.json()[:20]:
            item = {
                'number': x.get('number'), 'title': x.get('title',''), 'state': x.get('state'),
                'draft': bool(x.get('draft')), 'author': (x.get('user') or {}).get('login'),
                'head': (x.get('head') or {}).get('ref'), 'base': (x.get('base') or {}).get('ref'),
                'created_at': x.get('created_at'), 'updated_at': x.get('updated_at'), 'merged_at': x.get('merged_at'),
                'review_states': [],
            }
            if include_reviews and client is not None and x.get('number'):
                rr = client.get(f"/repos/{repo_full_name}/pulls/{x['number']}/reviews", params={'per_page': 100})
                if rr.is_success and isinstance(rr.json(), list):
                    item['review_states'] = [
                        {'reviewer': (r.get('user') or {}).get('login'), 'state': r.get('state'), 'submitted_at': r.get('submitted_at')}
                        for r in rr.json() if r.get('state')
                    ][:20]
            out.append(item)
        return out

    def head_sha(self, repo_full_name: str) -> str:
        if not repo_full_name or repo_full_name.startswith('demo/'):
            return 'demo-baseline'
        headers = self._headers_for(repo_full_name)
        with httpx.Client(base_url=self.base, headers=headers, timeout=12.0, follow_redirects=True) as c:
            repo = c.get(f'/repos/{repo_full_name}')
            if repo.status_code == 404 and 'Authorization' not in headers:
                raise RuntimeError('Repository is private or not found. Configure GitHub App repository access.')
            repo.raise_for_status()
            default_branch = repo.json().get('default_branch', 'main')
            ref = c.get(f'/repos/{repo_full_name}/git/ref/heads/{default_branch}')
            ref.raise_for_status()
            return ref.json()['object']['sha']

    def analyze(self, repo_full_name: str, phase_id: str, prior_categories: list[str] | None = None) -> EvidenceSnapshotData:
        if not repo_full_name or repo_full_name.startswith('demo/'):
            return demo_snapshot(phase_id, repo_full_name or 'demo/comp330-f26-team-01', prior_categories=prior_categories)
        cache_key = (repo_full_name, phase_id)
        cached = self._cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < self.s.etis_repo_refresh_seconds:
            out = copy.deepcopy(cached[1])
            # Re-rank against review history even when the evidence scan itself is cached.
            out.challenge_candidates = [f.to_dict() for f in rank_challenges(
                [ReviewFinding(**{k: v for k, v in x.items() if k in ReviewFinding.__dataclass_fields__}) for x in out.findings],
                prior_categories=prior_categories,
                limit=self.s.etis_review_challenge_limit,
            )]
            return out
        try:
            headers = self._headers_for(repo_full_name)
            with httpx.Client(base_url=self.base, headers=headers, timeout=25.0, follow_redirects=True) as c:
                repo = c.get(f'/repos/{repo_full_name}')
                if repo.status_code == 404 and 'Authorization' not in headers:
                    raise RuntimeError('Repository is private or not found. Configure GitHub App repository access.')
                repo.raise_for_status()
                repo_json = repo.json()
                default_branch = repo_json.get('default_branch', 'main')
                ref = c.get(f'/repos/{repo_full_name}/git/ref/heads/{default_branch}')
                ref.raise_for_status()
                sha = ref.json()['object']['sha']
                tree = c.get(f'/repos/{repo_full_name}/git/trees/{sha}', params={'recursive': '1'})
                tree.raise_for_status()
                tree_entries = [x for x in tree.json().get('tree', []) if x.get('type') == 'blob']
                actual_paths = {x['path'] for x in tree_entries}

                issues = c.get(f'/repos/{repo_full_name}/issues', params={'state': 'all', 'per_page': 100})
                pulls = c.get(f'/repos/{repo_full_name}/pulls', params={'state': 'all', 'per_page': 100})
                actions = c.get(f'/repos/{repo_full_name}/actions/runs', params={'per_page': 20})
                tags = c.get(f'/repos/{repo_full_name}/tags', params={'per_page': 100})
                commits = c.get(f'/repos/{repo_full_name}/commits', params={'per_page': 100})
                branches = c.get(f'/repos/{repo_full_name}/branches', params={'per_page': 100})
                releases = c.get(f'/repos/{repo_full_name}/releases', params={'per_page': 20}) if phase_id in {'A5','A6'} else None

                action_runs = []
                if actions.is_success and isinstance(actions.json(), dict):
                    action_runs = [{
                        'name': r.get('name'), 'event': r.get('event'), 'status': r.get('status'),
                        'conclusion': r.get('conclusion'), 'head_sha': r.get('head_sha'),
                        'created_at': r.get('created_at'), 'updated_at': r.get('updated_at'),
                    } for r in actions.json().get('workflow_runs', [])[:15]]
                commit_summaries = []
                if commits.is_success and isinstance(commits.json(), list):
                    for x in commits.json()[:25]:
                        cj = x.get('commit') or {}
                        commit_summaries.append({
                            'sha': str(x.get('sha',''))[:12],
                            'message': str(cj.get('message','')).split('\n',1)[0][:240],
                            'author': ((x.get('author') or {}).get('login') or (cj.get('author') or {}).get('name')),
                            'date': (cj.get('author') or {}).get('date'),
                        })
                tag_summaries = []
                if tags.is_success and isinstance(tags.json(), list):
                    tag_summaries = [{'name': x.get('name'), 'sha': ((x.get('commit') or {}).get('sha') or '')[:12]} for x in tags.json()[:30]]
                branch_summaries = []
                if branches.is_success and isinstance(branches.json(), list):
                    branch_summaries = [{'name': x.get('name'), 'protected': bool(x.get('protected'))} for x in branches.json()[:30]]
                release_summaries = []
                if releases is not None and releases.is_success and isinstance(releases.json(), list):
                    release_summaries = [{
                        'tag_name': x.get('tag_name'), 'name': x.get('name'), 'draft': bool(x.get('draft')),
                        'prerelease': bool(x.get('prerelease')), 'published_at': x.get('published_at'),
                    } for x in releases.json()[:20]]

                metrics = {
                    'issue_count': self._json_count(issues, exclude_prs=True),
                    'issues': self._issue_summaries(issues),
                    'pr_count': self._json_count(pulls),
                    'pull_requests': self._pull_summaries(pulls, c, repo_full_name, include_reviews=phase_id in {'A4','A5','A6'}),
                    'actions_runs': int(actions.json().get('total_count', 0)) if actions.is_success and isinstance(actions.json(), dict) else 0,
                    'action_runs': action_runs,
                    'tag_count': self._json_count(tags),
                    'tags': tag_summaries,
                    'commit_count': self._json_count(commits),
                    'recent_commits': commit_summaries,
                    'branch_count': self._json_count(branches),
                    'branches': branch_summaries,
                    'releases': release_summaries,
                    'default_branch': default_branch,
                    'visibility': repo_json.get('visibility', 'unknown'),
                    'private': bool(repo_json.get('private')),
                    'repo_url': repo_json.get('html_url', ''),
                }

                # Content collection is intentionally phase-bounded. We inspect the evidence needed
                # for the current gate rather than sending the entire repository to the model.
                artifacts: list[ArtifactFact] = []
                for entry in tree_entries:
                    path = entry['path']
                    if not path_in_phase_scope(path, phase_id):
                        continue
                    size = int(entry.get('size') or 0)
                    if size > self.s.etis_max_repo_file_bytes:
                        artifacts.append(ArtifactFact(path=path, exists=True, size=size, provenance='UNKNOWN', quality='too_large', summary='Artifact exceeds the configured inspection limit.', url=f"https://github.com/{repo_full_name}/blob/{sha}/{path}"))
                        continue
                    blob = c.get(f"/repos/{repo_full_name}/git/blobs/{entry['sha']}")
                    if not blob.is_success:
                        continue
                    bj = blob.json()
                    try:
                        data = base64.b64decode(bj.get('content', '') if bj.get('encoding') == 'base64' else '')
                    except Exception:
                        data = b''
                    if data:
                        artifact = artifact_from_bytes(path, data, f"https://github.com/{repo_full_name}/blob/{sha}/{path}")
                        artifact.phase_scope, artifact.scope_reason = evidence_phase_scope(path, phase_id)
                        artifacts.append(artifact)
                result = build_snapshot(phase_id, repo_full_name, sha, actual_paths, metrics, artifacts, prior_categories=prior_categories)
                if self.s.etis_semantic_repository_review and self.semantic_assessor.available():
                    try:
                        semantic = self.semantic_assessor.assess(phase_id, repo_full_name, sha, result.artifacts, metrics)
                        result.semantic_review = {"enabled": True, "strength_count": len(semantic.strengths), "finding_count": len(semantic.findings), "model": self.s.openai_repository_model}
                        result.ai_usage_events = list(semantic.usage_events or [])
                        for strength in semantic.strengths:
                            if strength not in result.strengths:
                                result.strengths.append(strength)
                        result.strengths = result.strengths[:4]
                        existing_keys = {(x.get('category'), x.get('title')) for x in result.findings}
                        for finding in semantic.findings:
                            key = (finding.get('category'), finding.get('title'))
                            if key not in existing_keys:
                                result.findings.append(finding)
                                existing_keys.add(key)
                        result.equivalent_evidence = semantic.equivalent_evidence
                        if semantic.equivalent_evidence:
                            equivalents = {x.get('expected_path'): x for x in semantic.equivalent_evidence if x.get('confidence') in {'moderate','high'}}
                            for item in result.items:
                                eq = equivalents.get(item.title)
                                if eq and item.status == 'missing':
                                    item.status = 'equivalent'
                                    item.quality = 'reviewable'
                                    item.source_provenance = 'TEAM_ADDED'
                                    item.equivalent_path = eq.get('actual_path','')
                                    item.scope_reason = f"Equivalent evidence detected at {eq.get('actual_path','')}"
                            eq_paths=set(equivalents)
                            result.findings = [f for f in result.findings if not (f.get('category')=='missing_evidence' and any(ref == f"PATH:{ep}" for ep in eq_paths for ref in f.get('evidence_refs',[])))]
                            result.gaps = [g for g in result.gaps if not any(g.startswith(ep + ':') for ep in eq_paths)]
                            result.coverage = round(100 * sum(i.status in {'present','equivalent'} for i in result.items) / max(1,len(result.items)))
                        all_findings = [
                            ReviewFinding(**{k: v for k, v in x.items() if k in ReviewFinding.__dataclass_fields__})
                            for x in result.findings
                        ]
                        result.challenge_candidates = [f.to_dict() for f in rank_challenges(
                            all_findings, prior_categories=prior_categories, limit=self.s.etis_review_challenge_limit
                        )]
                    except Exception as exc:
                        result.semantic_review = {"enabled": False, "warning": f"Semantic repository review was unavailable: {type(exc).__name__}"}
                        result.warnings.append('Semantic repository interpretation was unavailable; deterministic FACT analysis remains valid.')
                else:
                    result.semantic_review = {"enabled": False, "warning": 'Semantic repository review is not configured.'}
                self._cache[cache_key] = (time.monotonic(), copy.deepcopy(result))
                return result
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            raise RuntimeError(f'GitHub evidence acquisition failed with HTTP {status}.') from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f'GitHub evidence acquisition could not reach GitHub: {exc}.') from exc


def build_snapshot(phase_id: str, repo_full_name: str, sha: str, actual_paths: Iterable[str], metrics: dict | None = None, artifacts: list[ArtifactFact] | None = None, prior_categories: list[str] | None = None):
    phase = get_phase(phase_id)
    paths = set(actual_paths)
    metrics = metrics or {'issue_count': 0, 'pr_count': 0, 'actions_runs': 0, 'tag_count': 0, 'commit_count': 0}
    artifacts = artifacts or []
    artifact_by_path = {a.path: a for a in artifacts}
    items: list[EvidenceItem] = []
    gaps: list[str] = []
    warnings: list[str] = []

    for idx, exp in enumerate(phase['expected_evidence'], start=1):
        p = exp['path']
        if p == 'GitHub Issues':
            ok = metrics.get('issue_count', 0) > 0
            detail = f"{metrics.get('issue_count', 0)} issue record(s) visible" if ok else 'No issue records visible'
            source_prov, quality = 'GITHUB', 'reviewable' if ok else 'missing'
        elif p == 'GitHub Pull Requests':
            ok = metrics.get('pr_count', 0) > 0
            detail = f"{metrics.get('pr_count', 0)} pull request(s) visible" if ok else 'No pull requests visible'
            source_prov, quality = 'GITHUB', 'reviewable' if ok else 'missing'
        else:
            ok = _path_matches(p, paths)
            detail = exp['claim']
            art = artifact_by_path.get(p)
            if not art and p.endswith('/'):
                children = [a for a in artifacts if a.path.startswith(p)]
                source_prov = 'BASELINE' if children and all(a.provenance == 'BASELINE' for a in children) else ('TEAM_ADAPTED' if children else 'UNKNOWN')
                quality = 'scaffold' if source_prov == 'BASELINE' else ('reviewable' if children else 'missing')
            else:
                source_prov = art.provenance if art else 'UNKNOWN'
                quality = art.quality if art else ('reviewable' if ok else 'missing')
        status = 'present' if ok else 'missing'
        if ok and source_prov == 'BASELINE':
            status = 'scaffold'
        elif ok and quality in {'thin', 'partial', 'empty'}:
            status = 'weak'
        item = EvidenceItem(ref=f'EV-{idx:03d}', kind='repository', status=status, title=p, detail=detail, provenance='FACT', source_provenance=source_prov, quality=quality, phase_scope='CURRENT_PHASE', scope_reason=f'{phase_id} expected evidence')
        items.append(item)
        if status != 'present':
            gaps.append(f"{p}: {status}")

    coverage = round(100 * sum(i.status in {'present','equivalent'} for i in items) / max(1, len(items)))
    findings = build_findings(phase_id, artifacts, metrics, phase['expected_evidence'])
    strengths = summarize_strengths(phase_id, artifacts, metrics)
    if not strengths and any(i.status in {'present', 'scaffold'} for i in items):
        strengths.append('The repository has a recognizable phase structure that can support progressively stronger engineering evidence.')
    if any(a.provenance == 'BASELINE' for a in artifacts):
        warnings.append('Starter-kit scaffolding is distinguished from team-authored engineering evidence.')
    warnings.append('FACT findings describe what the snapshot observed. REVIEW findings are challengeable engineering interpretations.')
    return EvidenceSnapshotData(
        phase_id=phase_id,
        repo_full_name=repo_full_name,
        commit_sha=sha,
        coverage=coverage,
        items=items,
        strengths=strengths,
        gaps=gaps,
        warnings=warnings,
        repository_metrics=metrics,
        artifacts=[a.to_dict() for a in artifacts],
        findings=[f.to_dict() for f in findings],
        challenge_candidates=[f.to_dict() for f in rank_challenges(findings, prior_categories=prior_categories, limit=get_settings().etis_review_challenge_limit)],
    )


def demo_snapshot(phase_id: str, repo_full_name='demo/comp330-f26-team-01', prior_categories: list[str] | None = None):
    # Demo models an untouched starter-kit-like repository so UI development exercises
    # the same baseline-vs-team-evidence distinction as the real acceptance test.
    phase = get_phase(phase_id)
    artifacts: list[ArtifactFact] = []
    items: list[EvidenceItem] = []
    for idx, exp in enumerate(phase['expected_evidence'], 1):
        path = exp['path']
        if path.startswith('GitHub '):
            items.append(EvidenceItem(ref=f'EV-{idx:03d}', kind='repository', status='missing', title=path, detail=exp['claim'], freshness='demo', source_provenance='GITHUB', quality='missing'))
            continue
        # Directory evidence is represented by one synthetic baseline child for demo only.
        art_path = path if not path.endswith('/') else path + 'starter-placeholder.md'
        artifacts.append(ArtifactFact(path=art_path, exists=True, provenance='BASELINE', quality='scaffold', summary='Demo starter-kit scaffold.'))
        items.append(EvidenceItem(ref=f'EV-{idx:03d}', kind='repository', status='scaffold', title=path, detail=exp['claim'], freshness='demo', source_provenance='BASELINE', quality='scaffold'))
    metrics = {'issue_count': 0, 'pr_count': 0, 'actions_runs': 0, 'tag_count': 0, 'commit_count': 1}
    findings = build_findings(phase_id, artifacts, metrics, phase['expected_evidence'])
    strengths = ['The COMP 330 starter scaffold is structurally organized for lifecycle evidence.']
    return EvidenceSnapshotData(
        phase_id, repo_full_name, 'demo-baseline', 0, items, strengths,
        [f"{x.title}: {x.status}" for x in items if x.status != 'present'],
        ['DEMO snapshot: use repository analysis for real review decisions.'], metrics,
        [a.to_dict() for a in artifacts], [f.to_dict() for f in findings],
        [f.to_dict() for f in rank_challenges(findings, prior_categories=prior_categories, limit=get_settings().etis_review_challenge_limit)], 'demo',
    )



def snapshot_from_dict(data: dict) -> EvidenceSnapshotData:
    items = [EvidenceItem(**{k: v for k, v in item.items() if k in EvidenceItem.__dataclass_fields__}) for item in data.get('items', [])]
    return EvidenceSnapshotData(
        phase_id=data.get('phase_id',''), repo_full_name=data.get('repo_full_name',''), commit_sha=data.get('commit_sha',''),
        coverage=int(data.get('coverage') or 0), items=items, strengths=list(data.get('strengths') or []),
        gaps=list(data.get('gaps') or []), warnings=list(data.get('warnings') or []), repository_metrics=dict(data.get('repository_metrics') or {}),
        artifacts=list(data.get('artifacts') or []), findings=list(data.get('findings') or []), challenge_candidates=list(data.get('challenge_candidates') or []),
        snapshot_kind=data.get('snapshot_kind','github'), longitudinal=data.get('longitudinal'), equivalent_evidence=data.get('equivalent_evidence'),
        semantic_review=data.get('semantic_review'), ai_usage_events=list(data.get('ai_usage_events') or []),
    )
