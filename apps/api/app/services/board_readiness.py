from __future__ import annotations

from .course_model import get_phase
from .artifact_condition import condition_for, supported_observations

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


def build_phase_preparation(phase_id: str, evidence) -> dict:
    """Current, bounded coaching priorities from one frozen phase snapshot.

    This is a presentation projection. In particular, absence of a finding is
    never a positive assessment, and a professional stretch question is not a
    course requirement. Accept both stored dictionaries and live snapshots.
    """
    def field(value, name, default=None):
        return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)

    items = [x if isinstance(x, dict) else vars(x) for x in (field(evidence, 'items', []) or [])]
    findings = [f for f in (field(evidence, 'findings', []) or []) if isinstance(f, dict)]
    supports = field(evidence, 'claim_support', []) or []
    conditions = [(item, condition_for(item, findings, supports)) for item in items]
    active = [f for f in findings if not f.get('positive')
              and (f.get('lifecycle') or {}).get('status', 'open') not in {'corrected', 'resolved'}]
    course = [f for f in active if f.get('review_scope', 'course_readiness') != 'professional_challenge']
    course.sort(key=lambda f: (int(f.get('rank_score') or 0), int(f.get('severity') or 0)), reverse=True)

    focus = None
    if course:
        finding = course[0]
        linked = next(((item, state) for item, state in conditions
                       if state.get('finding_id') == finding.get('id')), None)
        focus = {
            'kind': 'review_interpretation', 'title': finding.get('title') or 'Review this concern',
            'why': finding.get('statement') or '',
            'next_step': (linked[1]['next_step'] if linked else
                          'Inspect the cited frozen evidence; ask the reviewer to explain or challenge this interpretation, then decide what to change.'),
            'evidence_refs': list(finding.get('evidence_refs') or []),
            'finding_id': finding.get('id'),
        }
    else:
        gap = next(((item, state) for item, state in conditions if state['key'] == 'gap'), None)
        if gap:
            focus = {'kind': 'evidence_gap', 'title': gap[0].get('title') or 'Evidence area',
                     'why': gap[1]['why'], 'next_step': gap[1]['next_step'],
                     'evidence_refs': [gap[0].get('title') or ''], 'finding_id': None}

    grounded = []
    for item, state in conditions:
        if state['key'] not in {'strong', 'okay'}:
            continue
        support = state['support']
        grounded.append({'label': state['label'], 'path': item.get('title') or '',
                         'claim': support['claim'], 'source_path': support['support_path'],
                         'source_paths': [support['support_path'],
                                          *(r['path'] for r in support.get('corroborating_evidence', []))],
                         'support_kind': support['support_kind'],
                         'limitation': support['limitation']})
    unknowns = [{'path': item.get('title') or '', 'why': state['why']}
                for item, state in conditions if state['key'] in {'unknown', 'verify'}]
    return {
        'phase_id': phase_id,
        'focus': focus,
        'supported': grounded[:3],
        'unknowns': unknowns[:2],
        'professional_questions': sum(f.get('review_scope') == 'professional_challenge' for f in active),
        'boundary': ('This is preparation using the frozen repository snapshot and challengeable REVIEW interpretations. '
                     'It does not predict an instructor decision or grade. A changed repository needs a new review.'),
    }


def build_board_readout(phase_id: str, evidence) -> dict:
    phase = get_phase(phase_id)
    def field(name, default=None):
        return evidence.get(name, default) if isinstance(evidence, dict) else getattr(evidence, name, default)

    findings = list(field("challenge_candidates", []) or field("findings", []) or [])
    findings = [f for f in findings if not f.get("positive")
                and (f.get('lifecycle') or {}).get('status', 'open') not in {'corrected', 'resolved'}]
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

    strengths = supported_observations(evidence)[:3]
    dimensions = []
    # A phrase in a finding is not a validated assessment of an entire phase
    # dimension. Preserve the useful phase topics without inferring health or
    # readiness from keyword overlap; the agenda contains the actual findings.
    for name, _keywords in PHASE_DIMENSIONS.get(phase_id, []):
        dimensions.append({"name": name, "status": "Not independently assessed"})

    primary = next((row for row in agenda if row['review_scope'] != 'professional_challenge'), None)
    if primary:
        assessment = (
            f"Let's improve your {phase_id} work before the instructor review. "
            f"The first thing to examine is {primary['title']}."
        )
    else:
        assessment = (
            f"No current course concern was selected from the {phase_id} snapshot. "
            "Let's examine a consequential engineering decision together; this does not establish phase readiness."
        )

    metrics = field("repository_metrics", {}) or {}
    tags = list(metrics.get("tags") or [])
    tag_count = int(metrics.get("tag_count", 0) or 0)
    current_sha = str(field("commit_sha", "") or "")
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
        "preparation": build_phase_preparation(phase_id, evidence),
        "agenda": agenda[:6],
        "readiness_map": dimensions,
        "submission_baseline": submission_baseline,
        "steering_note": (
            "I will explain what the evidence supports and help you decide what to improve. "
            "You can ask for an example, point me to evidence, or challenge my interpretation at any time."
        ),
        "not_a_grade": True,
    }
