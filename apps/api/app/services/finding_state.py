from __future__ import annotations

import json
import re

CLOSED_FINDING_STATUSES = frozenset({"corrected", "resolved"})
KNOWN_FINDING_STATUSES = frozenset({
    "open", "under_discussion", "evidence_disputed", "confirmed",
    "corrected", "resolved", "accepted_risk", "deferred",
})

_POSITIVE_CLOSURE_PATTERNS = (
    re.compile(r"\b(?:this|that|the evidence|the file|the record)\s+(?:fully\s+)?(?:resolves|closes|clears)\s+(?:the\s+)?(?:finding|concern|issue)\b", re.I),
    re.compile(r"\b(?:the\s+)?(?:finding|concern|issue)\s+(?:is|has been|can be)\s+(?:now\s+)?(?:resolved|closed|cleared)\b", re.I),
    re.compile(r"\bwe\s+can\s+(?:now\s+)?(?:close|resolve|clear)\s+(?:the\s+)?(?:finding|concern|issue)\b", re.I),
)


def _evidence_condition(artifact_registry: dict[str, dict] | None, preferred_evidence_path: str | None) -> str:
    registry = artifact_registry or {}
    path = str(preferred_evidence_path or "")
    artifact = registry.get(path) or {}
    provenance = str(artifact.get("provenance") or "UNKNOWN")
    quality = str(artifact.get("quality") or "unknown")
    if not path:
        return "no_preferred_artifact"
    if not artifact:
        return "artifact_not_registered"
    if provenance == "BASELINE" or quality == "scaffold":
        return "scaffold_only"
    if quality in {"empty", "thin", "partial"}:
        return "weak"
    if quality in {"uninspected", "too_large", "binary", "unknown"}:
        return "unknown"
    if provenance in {"TEAM_ADAPTED", "TEAM_ADDED"} and quality == "reviewable":
        return "project_evidence"
    return "mixed"


def authoritative_finding_state(*, finding_id: str | None, lifecycle: dict | None = None,
                                artifact_registry: dict[str, dict] | None = None,
                                preferred_evidence_path: str | None = None) -> dict:
    fid = str(finding_id or "")
    if not fid or fid.startswith("context:"):
        return {
            "finding_id": fid or None,
            "status": "not_applicable",
            "closure_state": "not_applicable",
            "can_claim_resolved": False,
            "evidence_condition": _evidence_condition(artifact_registry, preferred_evidence_path),
            "preferred_evidence_path": preferred_evidence_path,
            "reasoning_readiness_is_closure": False,
            "inspection_changes_state": False,
        }
    raw_status = str((lifecycle or {}).get("status") or "open").strip().lower()
    status = raw_status if raw_status in KNOWN_FINDING_STATUSES else "open"
    closed = status in CLOSED_FINDING_STATUSES
    return {
        "finding_id": fid,
        "status": status,
        "closure_state": "closed" if closed else "open",
        "can_claim_resolved": closed,
        "evidence_condition": _evidence_condition(artifact_registry, preferred_evidence_path),
        "preferred_evidence_path": preferred_evidence_path,
        "reasoning_readiness_is_closure": False,
        "inspection_changes_state": False,
    }


def finding_state_prompt_contract(state: dict | None) -> str:
    state = dict(state or {})
    if state.get("status") in {None, "not_applicable"}:
        return ""
    return (
        "AUTHORITATIVE_FINDING_STATE\n"
        + json.dumps(state, ensure_ascii=False, sort_keys=True)
        + "\nRules: This state is server-authoritative. A defensible student recommendation is not finding closure. "
          "Inspecting a file is not finding closure. Post-snapshot work cannot close this frozen finding. "
          "Unless can_claim_resolved is true, do not say or imply that the finding, concern, or issue is resolved, "
          "closed, cleared, or satisfied. You may explain what would change the state in a later review."
    )


def guard_reviewer_reply(text: str, state: dict | None) -> str:
    text = str(text or "")
    state = dict(state or {})
    if state.get("closure_state") != "open":
        return text
    if not any(pattern.search(text) for pattern in _POSITIVE_CLOSURE_PATTERNS):
        return text
    status = str(state.get("status") or "open").replace("_", " ")
    return text.rstrip() + (
        f" State note: the active finding remains {status} against this frozen snapshot. "
        "This turn did not resolve, correct, or close it."
    )


def recommendation_confirmation(state: dict | None, *, prefix: str = "") -> str:
    state = dict(state or {})
    status = str(state.get("status") or "not_applicable")
    closure = str(state.get("closure_state") or "not_applicable")
    lead = f"{prefix}your recommendation is recorded as the judgment you are prepared to defend."
    if closure == "open":
        label = status.replace("_", " ")
        return (
            f"{lead} The active finding remains {label} against this frozen snapshot. "
            "Recording a recommendation preserves your reasoning; it does not resolve, correct, or close the finding, "
            "and it does not turn later repository work into evidence for this snapshot. A new review can evaluate updated work."
        )
    if closure == "closed":
        label = status.replace("_", " ")
        return (
            f"{lead} The active finding is authoritatively marked {label}. "
            "That lifecycle state is separate from the recommendation itself; the recommendation records the judgment you chose to preserve."
        )
    return (
        f"{lead} Recording it preserves your reasoning and does not by itself change repository evidence or any finding lifecycle state."
    )
