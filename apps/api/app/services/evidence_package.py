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
    topic_phase: str = ''

    def to_dict(self):
        return asdict(self)

    def to_prompt_text(self, max_chars: int = 14000) -> str:
        data = self.to_dict()
        rendered = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(rendered) <= max_chars:
            return rendered

        # Preserve valid structured evidence under the prompt budget. Artifact
        # bodies are the expandable portion; metadata and frozen-snapshot
        # identity remain intact.
        artifacts = data.get("relevant_artifacts") or []
        while len(rendered) > max_chars:
            candidates = [
                artifact
                for artifact in artifacts
                if artifact.get("content_excerpt")
            ]
            if not candidates:
                break

            artifact = max(
                candidates,
                key=lambda item: len(item.get("content_excerpt") or ""),
            )
            content = artifact.get("content_excerpt") or ""
            excess = len(rendered) - max_chars
            trim_by = max(excess, max(1, len(content) // 4))
            keep = max(0, len(content) - trim_by)
            artifact["content_excerpt"] = content[:keep]

            rendered = json.dumps(
                data,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        if len(rendered) > max_chars:
            # Extremely small caller budgets cannot carry the full package.
            # Return a minimal but still valid statement of the evidence
            # boundary rather than malformed JSON.
            minimal = {
                "phase_id": self.phase_id,
                "repo_full_name": self.repo_full_name,
                "commit_sha": self.commit_sha,
                "evidence_boundary": self.evidence_boundary,
            }
            rendered = json.dumps(
                minimal,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return rendered


class EvidencePackageBuilder:
    """Builds a bounded, reusable evidence package for a single review conversation.

    The entire repository snapshot stays server-side. The model receives only facts relevant
    to the selected challenge plus compact phase/workflow context. This reduces cost and makes
    the review's epistemic boundary inspectable.
    """

    @staticmethod
    def _supported_paths(evidence: dict, paths: list[str]) -> list[str]:
        """Follow validated claim citations within the same frozen snapshot."""
        selected = list(dict.fromkeys(paths))
        for support in evidence.get('claim_support') or []:
            cited = [support.get('support_path'),
                     *(r.get('path') for r in support.get('corroborating_evidence') or [])]
            if support.get('expected_path') not in selected and not any(p in selected for p in cited):
                continue
            for path in cited:
                if path and path not in selected:
                    selected.append(path)
        return selected

    @staticmethod
    def _model_safe_artifact(
        artifact: dict,
        max_chars: int,
        content_field: str = "content_excerpt",
        include_windows: bool = False,
    ) -> dict:
        path = artifact.get("path") or ""
        content = artifact.get(content_field) or artifact.get("content_excerpt") or ""
        if include_windows:
            later = [w for w in (artifact.get("analysis_windows") or [])[:1 if max_chars < 3000 else 2]
                     if isinstance(w, dict) and isinstance(w.get("text"), str)]
            labelled = "".join(
                f"\n\n[Frozen excerpt, characters {w.get('start')}–{w.get('end')}]\n{w['text'][:900]}"
                for w in later
            )
            content = content[:max(0, max_chars - len(labelled))] + labelled[:max_chars]
        disclosure = sanitize_model_artifact(
            path,
            content[:max_chars],
        )

        if "sensitive_file" in disclosure.redactions:
            disclosure_status = "quarantined"
        elif disclosure.redactions:
            disclosure_status = "redacted"
        else:
            disclosure_status = "clear"

        if artifact.get("quality") in {"uninspected", "too_large", "binary"}:
            hydration_status = "FOUND_BUT_UNINSPECTED"
        elif "sensitive_file" in disclosure.redactions:
            hydration_status = "FOUND_BUT_QUARANTINED"
        elif artifact.get("quality") == "empty":
            hydration_status = "FOUND_BUT_EMPTY"
        elif not content:
            hydration_status = "FOUND_BUT_UNAVAILABLE"
        elif disclosure.text:
            hydration_status = "FOUND_AND_SUPPLIED"
        else:
            hydration_status = "FOUND_BUT_UNAVAILABLE"

        return {
            "path": path,
            "provenance": artifact.get("provenance"),
            "quality": artifact.get("quality"),
            "summary": artifact.get("summary"),
            "content_excerpt": disclosure.text,
            "disclosure_status": disclosure_status,
            "disclosure_reasons": list(disclosure.redactions),
            "hydration_status": hydration_status,
            "source_size": artifact.get("size", 0),
            "source_sha256": artifact.get("sha256", ""),
            "content_truncated": bool(
                content and (len(content) > max_chars or len(disclosure.text) < min(len(content), max_chars))
            ),
        }

    def build_for_turn(
        self,
        evidence: dict,
        challenge: dict,
        evidence_refs: list[str] | tuple[str, ...],
    ) -> CompactEvidencePackage:
        """Build model context for an explicit student evidence selection.

        Selected PATH references are resolved only against the supplied frozen
        evidence snapshot. They receive the larger review_content representation;
        unrelated repository artifacts are not added.
        """
        selected_paths = []
        for ref in evidence_refs or []:
            if isinstance(ref, str) and ref.startswith("PATH:"):
                path = ref[5:]
                if path and path not in selected_paths:
                    selected_paths.append(path)

        if not selected_paths:
            return self.build(evidence, challenge)
        selected_paths = self._supported_paths(evidence, selected_paths)[:3]

        selected = []
        by_path = {
            artifact.get("path"): artifact
            for artifact in evidence.get("artifacts", [])
            if artifact.get("path")
        }
        for path in selected_paths:
            artifact = by_path.get(path)
            if artifact is not None:
                selected.append(
                    self._model_safe_artifact(
                        artifact,
                        max_chars=8000 if len(selected_paths) == 1 else max(2200, 8000 // len(selected_paths)),
                        content_field="review_content",
                        include_windows=True,
                    )
                )
            else:
                selected.append({
                    "path": path,
                    "provenance": "UNKNOWN",
                    "quality": "missing",
                    "summary": "The selected path is not present in this frozen snapshot.",
                    "content_excerpt": "",
                    "disclosure_status": "clear",
                    "disclosure_reasons": [],
                    "hydration_status": "PATH_NOT_IN_SNAPSHOT",
                    "source_size": 0,
                    "source_sha256": "",
                    "content_truncated": False,
                })

        base = self.build(evidence, challenge)
        base.relevant_artifacts = selected
        base.evidence_boundary = (
            f'Frozen {evidence.get("phase_id")} snapshot at {evidence.get("commit_sha")}; '
            'exact selected paths take precedence for this turn. Each selected artifact includes '
            'an explicit hydration_status describing whether frozen content was actually supplied. '
            'Do not claim to have inspected file contents unless hydration_status is FOUND_AND_SUPPLIED '
            'or FOUND_BUT_EMPTY. Absence in the snapshot is not proof of absence everywhere.'
        )
        return base

    def build_for_phase(self, evidence: dict, challenge: dict, topic_phase: str,
                        evidence_refs=()) -> CompactEvidencePackage:
        """Retrieve bounded earlier-phase sources from the same frozen snapshot.

        Paths are discovery clues, not proof of a practice. Uninspected and
        scaffold sources remain labeled as such in the model package.
        """
        terms = {
            'A1': ('readme', 'team/', 'roles', 'working.agreement', 'stakeholder',
                   'requirements', 'launch', 'scope', 'decision'),
            'A2': ('requirements', 'planning/', 'estimate', 'risk', 'schedule',
                   'traceab', 'task', 'decision'),
            'A3': ('architecture', 'interface', 'contract', 'data.context', 'decision'),
            'A4': ('src/', 'tests/', 'testing', 'implementation', '.github/workflows', 'review'),
            'A5': ('release', 'acceptance', 'test.evidence', 'quality', 'risk'),
            'A6': ('operations', 'runbook', 'observab', 'recovery', 'security'),
        }.get(topic_phase, ())
        selected = {str(ref)[5:] for ref in (evidence_refs or [])
                    if str(ref).startswith('PATH:')}
        later_terms = {
            'A1': ('architecture', 'testing/', 'release/', 'src/', 'tests/', 'planning/estimat'),
            'A2': ('architecture/', 'release/', 'src/', 'tests/'),
            'A3': ('release/',),
        }.get(topic_phase, ())
        content_signals = {
            'A1': ('problem', 'stakeholder', 'scope', 'success', 'decision owner'),
            'A2': ('requirement', 'estimate', 'dependency', 'schedule', 'risk'),
            'A3': ('component', 'interface', 'boundary', 'data flow', 'architecture'),
            'A4': ('implementation', 'pull request', 'test result', 'integration', 'review'),
            'A5': ('acceptance', 'release', 'defect', 'residual risk', 'verification'),
            'A6': ('runbook', 'monitor', 'restore', 'incident', 'operation'),
        }.get(topic_phase, ())
        ranked = []
        for artifact in evidence.get('artifacts') or []:
            path = str(artifact.get('path') or '')
            if not path or not (path.startswith(('docs/', 'src/', 'tests/', '.github/'))
                                or path in {'README.md', 'CONTRIBUTING.md'}):
                continue
            lower = path.lower()
            if path not in selected and any(term in lower for term in later_terms):
                continue
            score = sum(3 if term in lower else 0 for term in terms)
            excerpt = str(artifact.get('content_excerpt') or '')[:4000].lower()
            content_hits = sum(term in excerpt for term in content_signals)
            if path.startswith('docs/') and content_hits >= 2:
                score += min(content_hits, 3)
            if path in selected:
                score += 100
            if score:
                # Team-authored content gets inspection priority, but the
                # evidence package does not turn that into a quality verdict.
                score += 4 if artifact.get('provenance') in {'TEAM_ADDED', 'TEAM_ADAPTED'} else 0
                ranked.append((score, path, artifact))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        candidates = [a for _, _, a in ranked[:7]]
        base = self.build(evidence, challenge)
        base.topic_phase = topic_phase
        base.challenge = {'active_topic': topic_phase, 'current_gate': evidence.get('phase_id')}
        base.strengths = []  # current-gate praise does not establish earlier work
        base.relevant_items = []  # these are current-gate expected locations
        base.relevant_artifacts = [self._model_safe_artifact(
            a, max_chars=2200 if a.get('path') in selected else 1300,
            content_field='review_content' if a.get('path') in selected else 'content_excerpt',
            include_windows=True,
        ) for a in candidates]
        base.evidence_boundary = (
            f'Frozen {evidence.get("phase_id")} snapshot; these are bounded, path-discovered '
            f'{topic_phase} candidates, not a complete earlier-phase assessment. '
            'A filename or polished policy alone does not prove performed practice. '
            'Uninspected, omitted, or equivalent evidence elsewhere remains unknown.'
        )
        return base

    def build(self, evidence: dict, challenge: dict) -> CompactEvidencePackage:
        refs = set(challenge.get("evidence_refs") or [])
        # Board Review is intentionally steerable. Include bounded evidence for the
        # executive agenda, not only the first issue, so a student can say "I want
        # to discuss the security finding instead" without leaving the frozen snapshot.
        readout = challenge.get("board_readout") or {}
        for agenda_item in readout.get("agenda", [])[:6]:
            refs.update(agenda_item.get("evidence_refs") or [])
        paths = {r[5:] for r in refs if isinstance(r, str) and r.startswith("PATH:")}
        paths.update(self._supported_paths(evidence, list(paths))[:8])
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
                    self._model_safe_artifact(art, max_chars=1800, include_windows=True)
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
                "board_readout": challenge.get("board_readout"),
            },
            relevant_items=items[:10],
            relevant_artifacts=artifacts[:8],
            github_signals=github,
            longitudinal=evidence.get("longitudinal") or {},
            evidence_boundary="Facts describe only the frozen snapshot. Absence in the snapshot is not proof of absence everywhere; REVIEW interpretations remain challengeable.",
        )
