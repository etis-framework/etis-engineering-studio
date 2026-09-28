import copy
import time
from types import SimpleNamespace

from apps.api.app.services import evidence as evidence_module
from apps.api.app.services.evidence import GitHubEvidenceProvider, build_snapshot
from apps.api.app.services.repository_intelligence import ArtifactFact


def test_located_but_uninspected_expected_file_is_not_coverage():
    path = 'docs/planning/estimates.md'
    artifact = ArtifactFact(path=path, exists=True, quality='too_large', summary='Artifact exceeds inspection limit.')
    snapshot = build_snapshot('A2', 'team/repo', 'frozen-sha', [path], artifacts=[artifact])
    item = next(x for x in snapshot.items if x.title == path)
    assert item.status == 'uninspected'
    assert item.quality == 'too_large'
    assert item.detail == artifact.summary
    assert snapshot.coverage == 0
    assert any(f['category'] == 'inspection_boundary' for f in snapshot.findings)


def test_tree_path_with_failed_blob_is_not_content_evidence():
    path = 'docs/planning/estimates.md'
    snapshot = build_snapshot('A2', 'team/repo', 'frozen-sha', [path], artifacts=[])
    item = next(x for x in snapshot.items if x.title == path)
    assert item.status == 'uninspected'
    assert snapshot.coverage == 0


def test_new_commit_cannot_reuse_previous_commit_memory_cache(monkeypatch):
    old = build_snapshot('A2', 'team/repo', 'old-sha', [], artifacts=[])
    provider = GitHubEvidenceProvider.__new__(GitHubEvidenceProvider)
    provider.s = SimpleNamespace(etis_repo_refresh_seconds=3600, etis_max_repo_file_bytes=262144,
                                 etis_semantic_repository_review=False)
    provider.semantic_assessor = SimpleNamespace(available=lambda: False)
    provider._cache = {('team/repo', 'A2', 'old-sha'): (time.monotonic(), copy.deepcopy(old))}
    provider.base = 'https://api.github.com'
    provider._headers_for = lambda repo: {}

    class Response:
        is_success = True
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, path, **kwargs):
            if path == '/repos/team/repo':
                return Response({'default_branch': 'main'})
            if path.endswith('/git/ref/heads/main'):
                return Response({'object': {'sha': 'new-sha'}})
            if '/git/trees/' in path:
                return Response({'tree': []})
            if path.endswith('/actions/runs'):
                return Response({'workflow_runs': [], 'total_count': 0})
            return Response([])

    monkeypatch.setattr(evidence_module.httpx, 'Client', Client)
    current = provider.analyze('team/repo', 'A2', expected_sha='new-sha')
    assert current.commit_sha == 'new-sha'
    assert current is not old
