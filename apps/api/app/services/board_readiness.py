from __future__ import annotations

from .course_model import get_phase

# Student-facing readiness dimensions are deliberately phase-specific and non-numeric.
# They orient coaching; they are not a grade prediction or an autonomous gate verdict.
PHASE_DIMENSIONS = {
    "A1": [
        ("Project direction & vertical slice", ("scope", "requirement", "vertical", "decision")),
        ("Ownership & team operation", ("owner", "role", "team", "accountab", "working agreement")),
        ("Workflow & review discipline", ("workflow", "pull request", "review", "issue", "merge")),
        ("Risk, decisions & evidence", ("risk", "decision", "evidence", "trace")),
        ("AI governance & verification", ("ai", "verification", "disclosure")),
    ],
    "A2": [
        ("Requirements & scope", ("requirement", "scope", "vertical", "acceptance")),
        ("Work decomposition & ownership", ("task", "work breakdown", "owner", "issue")),
        ("Estimates & assumptions", ("estimate", "assumption", "confidence", "uncertainty")),
        ("Schedule & dependencies", ("schedule", "dependency", "milestone", "capacity")),
        ("Risks & re-estimation", ("risk", "re-estimat", "trigger")),
        ("Traceability & review evidence", ("trace", "review", "evidence")),
        ("AI use & verification", ("ai", "verification", "disclosure")),
    ],
    "A3": [
        ("Architecture responsibilities", ("architecture", "component", "responsib")),
        ("Interfaces & contracts", ("api", "interface", "contract")),
        ("Data, trust & security boundaries", ("data", "trust", "security", "privacy", "permission")),
        ("Architecture decisions & assumptions", ("decision", "adr", "assumption", "tradeoff")),
        ("Failure & quality attributes", ("failure", "reliab", "performance", "scale", "availability")),
        ("Review, traceability & verification plan", ("review", "trace", "test", "verification")),
    ],
    "A4": [
        ("Implementation & integration", ("implementation", "construction", "integration", "code")),
        ("Review controls", ("review", "pull request", "merge", "approval")),
        ("CI & automated evidence", ("ci", "action", "build", "automation")),
        ("Tests & defect prevention", ("test", "defect", "regression")),
        ("Architecture conformance", ("architecture", "boundary", "contract")),
        ("AI-assisted code verification", ("ai", "verification", "generated")),
    ],
    "A5": [
        ("Acceptance & traceability", ("acceptance", "requirement", "trace")),
        ("Verification evidence", ("test", "verification", "evidence", "regression")),
        ("Release baseline & change control", ("release", "baseline", "tag", "change")),
        ("Defects & residual risk", ("defect", "risk", "failure")),
        ("Operational evidence", ("deploy", "operation", "monitor", "runbook")),
        ("Release claims", ("claim", "ready", "complete", "works")),
    ],
    "A6": [
        ("Operational supportability", ("operation", "runbook", "support", "owner")),
        ("Observability & diagnosis", ("observ", "log", "monitor", "alert", "diagnos")),
        ("Recovery & resilience", ("recover", "backup", "restore", "failure", "resilien")),
        ("Security & governance", ("security", "privacy", "govern", "permission")),
        ("Release & verification evidence", ("release", "test", "verification", "acceptance")),
        ("Maintainability & evolution", ("maintain", "debt", "evol", "handoff")),
        ("Maturity claims", ("claim", "production", "ready", "mature")),
    ],
}


def _severity_label(value: int) -> str:
    if value >= 4:
        return "major"
    if value >= 2:
        return "issue"
    return "observation"


def _finding_text(finding: dict) -> str:
    return " ".join(str(finding.get(k, "")) for k in ("category", "title", "statement", "significance")).lower()


def build_board_readout(phase_id: str, evidence) -> dict:
    phase = get_phase(phase_id)
    findings = list(getattr(evidence, "challenge_candidates", []) or getattr(evidence, "findings", []) or [])
    findings = [f for f in findings if not f.get("positive")]
    findings.sort(key=lambda f: (int(f.get("rank_score", 0)), int(f.get("severity", 0))), reverse=True)

    counts = {"major": 0, "issue": 0, "observation": 0}
    agenda = []
    for f in findings:
        label = _severity_label(int(f.get("severity", 2)))
        counts[label] += 1
        agenda.append({
            "id": f.get("id"),
            "level": label,
            "title": f.get("title") or "Engineering review issue",
            "statement": f.get("statement") or "",
            "evidence_refs": list(f.get("evidence_refs") or []),
            "review_scope": f.get("review_scope", "course_readiness"),
            "reasoning_pattern": f.get("reasoning_pattern", "other"),
        })

    strengths = [str(x) for x in (getattr(evidence, "strengths", []) or []) if str(x).strip()][:3]
    dimensions = []
    all_findings = list(getattr(evidence, "findings", []) or [])
    for name, keywords in PHASE_DIMENSIONS.get(phase_id, []):
        related = [f for f in all_findings if any(k in _finding_text(f) for k in keywords)]
        worst = max((int(f.get("severity", 0)) for f in related), default=0)
        if worst >= 4:
            status = "Needs attention"
        elif worst >= 2:
            status = "Developing"
        else:
            status = "No material gap identified"
        dimensions.append({"name": name, "status": status})

    primary = agenda[0] if agenda else None
    if primary:
        assessment = (
            f"The board found {counts['major']} major issue{'s' if counts['major'] != 1 else ''}, "
            f"{counts['issue']} other issue{'s' if counts['issue'] != 1 else ''}, and "
            f"{counts['observation']} observation{'s' if counts['observation'] != 1 else ''} in the current {phase_id} evidence. "
            f"The board will begin with the highest-value concern: {primary['title']}."
        )
    else:
        assessment = (
            f"The current {phase_id} scan found no material repository gap above the board's review threshold. "
            "The board will still test consequential engineering judgment; artifact completeness alone does not establish readiness."
        )

    metrics = getattr(evidence, "repository_metrics", {}) or {}
    tags = list(metrics.get("tags") or [])
    tag_count = int(metrics.get("tag_count", 0) or 0)
    current_sha = str(getattr(evidence, "commit_sha", "") or "")
    matching_tags = [t.get("name") for t in tags if t.get("sha") and current_sha.startswith(str(t.get("sha")))]
    tag_note = ""
    if tag_count:
        if matching_tags:
            tag_note = f" Existing tag(s) on this reviewed commit: {', '.join(str(x) for x in matching_tags if x)}."
        else:
            tag_note = " Repository tags already exist, but Studio does not assume an existing tag is the intended submission baseline."
    submission_baseline = {
        "status": "in_preparation",
        "message": (
            "This Studio review is preparation for the phase gate. A phase-gate submission tag is not expected merely to use Studio. "
            "When the team is ready for final instructor review, merge the work intended for submission and create the required phase-gate tag on that exact commit."
            + tag_note
        ),
        "existing_tag_count": tag_count,
        "matching_tags": [x for x in matching_tags if x],
    }

    return {
        "phase_id": phase_id,
        "phase_title": phase.get("title", phase_id),
        "gate_question": phase.get("gate_question", ""),
        "assessment": assessment,
        "counts": counts,
        "strengths": strengths,
        "agenda": agenda[:6],
        "readiness_map": dimensions,
        "submission_baseline": submission_baseline,
        "steering_note": (
            "The board will guide the review and start with the most consequential issue. "
            "You can steer at any time by asking about another issue, challenging an interpretation, pointing to evidence, or making an engineering assertion."
        ),
        "not_a_grade": True,
    }
