from __future__ import annotations

import json
from dataclasses import dataclass, asdict

from .model_disclosure import sanitize_model_artifact


@dataclass
class CompactEvidencePackage:
    phase_id: str
    repo_full_name: str
    commit_sha: str
    strengths: list[str]
    challenge: dict
    relevant_items: list[dict]
    relevant_artifacts: list[dict]
    github_signals: dict
    longitudinal: dict
    evidence_boundary: str

    def to_dict(self):
        return asdict(self)

    def to_prompt_text(self, max_chars: int = 14000) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))[:max_chars]


class EvidencePackageBuilder:
    """Builds a bounded, reusable evidence package for a single review conversation.

    The entire repository snapshot stays server-side. The model receives only facts relevant
    to the selected challenge plus compact phase/workflow context. This reduces cost and makes
    the review's epistemic boundary inspectable.
    """

    @staticmethod
    def _model_safe_artifact(artifact: dict, max_chars: int) -> dict:
        path = artifact.get("path") or ""
        disclosure = sanitize_model_artifact(
            path,
            (artifact.get("content_excerpt") or "")[:max_chars],
        )

        if "sensitive_file" in disclosure.redactions:
            disclosure_status = "quarantined"
        elif disclosure.redactions:
            disclosure_status = "redacted"
        else:
            disclosure_status = "clear"

        return {
            "path": path,
            "provenance": artifact.get("provenance"),
            "quality": artifact.get("quality"),
            "summary": artifact.get("summary"),
            "content_excerpt": disclosure.text,
            "disclosure_status": disclosure_status,
            "disclosure_reasons": list(disclosure.redactions),
        }

    def build(self, evidence: dict, challenge: dict) -> CompactEvidencePackage:
        refs = set(challenge.get("evidence_refs") or [])
        paths = {r[5:] for r in refs if isinstance(r, str) and r.startswith("PATH:")}
        items = []
        for item in evidence.get("items", []):
            title = item.get("title") or ""
            if not paths or title in paths or any(title.startswith(p.rstrip("/") + "/") for p in paths):
                items.append({k: item.get(k) for k in ("ref", "status", "title", "detail", "provenance", "source_provenance", "quality", "phase_scope", "scope_reason", "equivalent_path", "url")})
        if not items:
            # Always provide a small phase-level sample so the reviewer can reason about boundaries.
            items = [{k: i.get(k) for k in ("ref", "status", "title", "detail", "provenance", "source_provenance", "quality", "phase_scope", "scope_reason", "equivalent_path", "url")} for i in evidence.get("items", [])[:8]]

        artifacts = []
        for art in evidence.get("artifacts", []):
            path = art.get("path") or ""
            if path in paths or any(path.startswith(p.rstrip("/") + "/") for p in paths):
                artifacts.append(
                    self._model_safe_artifact(art, max_chars=1800)
                )
        if not artifacts:
            # Include only a few high-information artifacts, never the entire repository.
            ranked = [a for a in evidence.get("artifacts", []) if a.get("quality") not in {"empty", "binary", "unknown"}]
            for art in ranked[:5]:
                artifacts.append(
                    self._model_safe_artifact(art, max_chars=1000)
                )

        metrics = evidence.get("repository_metrics") or {}
        github = {
            "issue_count": metrics.get("issue_count", 0),
            "pr_count": metrics.get("pr_count", 0),
            "actions_runs": metrics.get("actions_runs", 0),
            "tag_count": metrics.get("tag_count", 0),
            "commit_count": metrics.get("commit_count", 0),
            "branches": (metrics.get("branches") or [])[:8],
            "issues": (metrics.get("issues") or [])[:8],
            "pull_requests": (metrics.get("pull_requests") or [])[:6],
            "actions": (metrics.get("action_runs") or [])[:6],
        }
        return CompactEvidencePackage(
            phase_id=evidence.get("phase_id", ""),
            repo_full_name=evidence.get("repo_full_name", ""),
            commit_sha=evidence.get("commit_sha", ""),
            strengths=(evidence.get("strengths") or [])[:4],
            challenge={
                "title": challenge.get("title"),
                "finding": challenge.get("finding"),
                "decision_question": challenge.get("decision_question"),
                "why_now": challenge.get("why_now"),
            },
            relevant_items=items[:10],
            relevant_artifacts=artifacts[:8],
            github_signals=github,
            longitudinal=evidence.get("longitudinal") or {},
            evidence_boundary="Facts describe only the frozen snapshot. Absence in the snapshot is not proof of absence everywhere; REVIEW interpretations remain challengeable.",
        )
