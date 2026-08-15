from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from typing import Iterable
import httpx
from ..config import get_settings
from .course_model import get_phase


@dataclass
class EvidenceItem:
    ref: str
    kind: str
    status: str
    title: str
    detail: str
    url: str = ""
    freshness: str = "unknown"
    provenance: str = "FACT"


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

    def to_dict(self):
        d=asdict(self)
        return d


def _path_matches(expected: str, actual_paths: set[str]) -> bool:
    expected = expected.strip("/")
    if expected in {"GitHub Issues", "GitHub Pull Requests"}:
        return False
    if expected.endswith("/"):
        return any(p.startswith(expected) for p in actual_paths)
    return expected in actual_paths


class GitHubEvidenceProvider:
    """Read-only repository evidence acquisition.

    Wave 1 supports token-authenticated GitHub REST calls. The production architecture
    prefers a GitHub App installation so repository read authority is explicit, scoped,
    revocable, and does not require students to share personal access tokens.
    """

    def __init__(self, token: str | None = None):
        settings=get_settings()
        self.token = token or settings.github_token
        self.base = "https://api.github.com"
        self.headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def analyze(self, repo_full_name: str, phase_id: str) -> EvidenceSnapshotData:
        if not self.token:
            return demo_snapshot(phase_id, repo_full_name or "demo/team")
        with httpx.Client(base_url=self.base, headers=self.headers, timeout=20.0) as c:
            repo=c.get(f"/repos/{repo_full_name}")
            repo.raise_for_status()
            default_branch=repo.json().get("default_branch","main")
            ref=c.get(f"/repos/{repo_full_name}/git/ref/heads/{default_branch}")
            ref.raise_for_status()
            sha=ref.json()["object"]["sha"]
            tree=c.get(f"/repos/{repo_full_name}/git/trees/{sha}", params={"recursive":"1"})
            tree.raise_for_status()
            actual_paths={x["path"] for x in tree.json().get("tree",[]) if x.get("type")=="blob"}
            issues=c.get(f"/repos/{repo_full_name}/issues", params={"state":"all","per_page":100})
            pulls=c.get(f"/repos/{repo_full_name}/pulls", params={"state":"all","per_page":100})
            issue_count=len([i for i in issues.json() if "pull_request" not in i]) if issues.is_success else 0
            pr_count=len(pulls.json()) if pulls.is_success else 0
            return build_snapshot(phase_id, repo_full_name, sha, actual_paths, issue_count, pr_count)


def build_snapshot(phase_id: str, repo_full_name: str, sha: str, actual_paths: Iterable[str], issue_count=0, pr_count=0):
    phase=get_phase(phase_id)
    paths=set(actual_paths)
    items=[]; strengths=[]; gaps=[]; warnings=[]
    for idx, exp in enumerate(phase["expected_evidence"], start=1):
        p=exp["path"]
        if p=="GitHub Issues":
            ok=issue_count>0
            detail=f"{issue_count} issue records visible" if ok else "No issue records visible"
        elif p=="GitHub Pull Requests":
            ok=pr_count>0
            detail=f"{pr_count} pull requests visible" if ok else "No pull requests visible"
        else:
            ok=_path_matches(p, paths)
            detail=exp["claim"]
        status="present" if ok else "missing"
        items.append(EvidenceItem(ref=f"EV-{idx:03d}",kind="repository",status=status,title=p,detail=detail))
        (strengths if ok else gaps).append(f"{p}: {'visible' if ok else 'not yet evidenced'}")
    coverage=round(100*sum(i.status=="present" for i in items)/max(1,len(items)))
    if coverage==100:
        warnings.append("Presence is not proof of quality; content and workflow still require review.")
    if any(re.search(r"README|template", p, re.I) for p in paths):
        warnings.append("Starter/template presence must not be treated as completed engineering evidence.")
    return EvidenceSnapshotData(phase_id,repo_full_name,sha,coverage,items,strengths,gaps,warnings)


def demo_snapshot(phase_id: str, repo_full_name="demo/comp330-f26-team-01"):
    phase=get_phase(phase_id)
    items=[]
    # Deliberately mixed evidence so the demo yields meaningful challenges.
    present = {
        "A1":{"README.md","docs/team/team-charter.md","docs/team/roles.md","docs/ai/ai-policy.md","docs/requirements/","docs/planning/"},
        "A2":{"docs/planning/README.md","docs/planning/scope.md","docs/planning/task-plan.md","docs/planning/estimates.md","docs/planning/risk-register.md","GitHub Issues"}
    }.get(phase_id,set())
    for idx, exp in enumerate(phase["expected_evidence"], start=1):
        ok=exp["path"] in present
        detail=exp["claim"] if ok else f"Expected but not yet supported: {exp['claim']}"
        items.append(EvidenceItem(ref=f"EV-{idx:03d}",kind="repository",status="present" if ok else "gap",title=exp["path"],detail=detail,freshness="demo"))
    cov=round(100*sum(i.status=="present" for i in items)/max(1,len(items)))
    gaps=[f"{i.ref} {i.title}" for i in items if i.status!="present"]
    strengths=[f"{i.ref} {i.title}" for i in items if i.status=="present"]
    warnings=["DEMO snapshot: representative evidence only; no external repository was read."]
    return EvidenceSnapshotData(phase_id,repo_full_name,"demo-sha-001",cov,items,strengths,gaps,warnings)
