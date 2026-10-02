import json

from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers.reviews import (
    _authoritative_turn_context,
    _finding_family,
    _finding_family_from_text,
)
from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.services.evidence import (
    ANALYSIS_CONTRACT,
    build_snapshot,
    supports_current_analysis_contract,
)
from apps.api.app.services.repository_intelligence import ArtifactFact


def artifact(path, content, *, provenance="BASELINE", quality="scaffold"):
    return ArtifactFact(
        path=path,
        exists=True,
        provenance=provenance,
        quality=quality,
        summary=f"{path} synthetic frozen artifact",
        content_excerpt=content,
        review_content=content,
        size=len(content.encode()),
        sha256="sha-" + path.replace("/", "-"),
    )


def evidence_fixture():
    arts = [
        artifact(
            "docs/architecture/architecture.md",
            "system context components interfaces constraints diagram decisions",
        ),
        artifact(
            "docs/ai/ai-use-log.md",
            "date tool purpose artifact human verification outcome",
        ),
        artifact(
            "docs/planning/risk-register.md",
            "risk likelihood impact mitigation owner status reassessment trigger",
        ),
        artifact(
            "docs/decisions/ADR-000-template.md",
            "context decision alternatives rationale consequences revisit",
        ),
        artifact(
            "docs/testing/test-strategy.md",
            "testing verification exit criteria evidence",
        ),
        artifact(
            ".github/workflows/ci.yml",
            "manual workflow project CI not configured failure",
        ),
        artifact(
            "CONTRIBUTING.md",
            "architecture risk decisions AI verification process",
            quality="reviewable",
        ),
    ]
    ev = build_snapshot(
        "A3",
        "team/repo",
        "same-sha",
        [a.path for a in arts],
        artifacts=arts,
    )
    ev.findings = [
        {
            "id": "verification-opening",
            "category": "verification",
            "title": "Architecture verification is not demonstrated",
            "statement": "The snapshot does not demonstrate operating architecture verification.",
            "significance": "Architecture risks and contracts remain unverified.",
            "evidence_refs": ["PATH:docs/testing/test-strategy.md"],
            "suggested_lens": "delivery",
        }
    ]
    ev.challenge_candidates = list(ev.findings)
    return ev


class FakeDB:
    def __init__(self, ev):
        self.row = type(
            "SnapshotRow",
            (),
            {
                "summary_json": json.dumps(ev.to_dict()),
                "commit_sha": ev.commit_sha,
            },
        )()

    def get(self, model, key):
        assert model is EvidenceSnapshot
        return self.row


def initial_state(ev):
    opening = ChallengeEngine(ai=object()).start("A3", ev)
    return {
        "challenge": opening.to_dict(),
        "evidence_snapshot_id": 7,
        "active_finding_id": opening.id,
        "active_family": "verification",
        "active_finding_by_family": {"verification": opening.id},
        "compact_evidence_package": {},
        "active_turn_context": None,
    }


def advance(state, ctx):
    state["active_family"] = ctx["active_family"]
    state["active_turn_context"] = {
        "active_family": ctx["active_family"],
        "preferred_evidence_path": ctx["preferred_evidence_path"],
        "retrieval_mode": ctx["retrieval_mode"],
        "snapshot_id": ctx["snapshot_id"],
        "commit_sha": ctx["commit_sha"],
    }


def test_analysis_contract_v3_invalidates_prior_interpretation():
    assert ANALYSIS_CONTRACT == "authoritative_turn_context_v3"
    assert not supports_current_analysis_contract(
        {
            "semantic_review": {
                "analysis_contract": "starter_lineage_active_context_v2"
            }
        }
    )


def test_family_resolution_prefers_category_and_architecture_decision_is_decision():
    assert _finding_family_from_text(
        "Find our architecture decisions and ADRs"
    ) == "decision"
    assert _finding_family(
        {
            "category": "verification",
            "title": "Architecture verification gap",
            "statement": "Verification is absent.",
            "significance": "Architecture risks remain.",
        }
    ) == "verification"


def test_production_sequence_keeps_authoritative_family_and_target():
    ev = evidence_fixture()
    db = FakeDB(ev)
    state = initial_state(ev)

    sequence = [
        (
            "Search the frozen repository and tell me what supports an architecture baseline.",
            "architecture",
            "docs/architecture/architecture.md",
        ),
        (
            "Take the strongest candidate you found. What does it actually prove?",
            "architecture",
            "docs/architecture/architecture.md",
        ),
        (
            "Search the repository for our AI use or non-use evidence.",
            "ai",
            "docs/ai/ai-use-log.md",
        ),
        (
            "Search the repository for evidence that we identified and managed meaningful project risks.",
            "risk",
            "docs/planning/risk-register.md",
        ),
        (
            "I know we did this somewhere. Find it.",
            "risk",
            "docs/planning/risk-register.md",
        ),
        (
            "Find the strongest architecture decision evidence in the repository.",
            "decision",
            "docs/decisions/ADR-000-template.md",
        ),
        (
            "Does this actually resolve it?",
            "decision",
            "docs/decisions/ADR-000-template.md",
        ),
        (
            "I thought the evidence was in docs/architecture/data-context.md, but I may be remembering the path wrong. Search the frozen repository for architecture evidence.",
            "architecture",
            "docs/architecture/architecture.md",
        ),
        (
            "Go back to the architecture finding. Search the repository again.",
            "architecture",
            "docs/architecture/architecture.md",
        ),
    ]

    for text, family, expected_path in sequence:
        refs = (
            ["PATH:docs/architecture/data-context.md"]
            if "data-context.md" in text
            else []
        )
        ctx = _authoritative_turn_context(db, state, refs, text)
        assert ctx["active_family"] == family
        assert ctx["preferred_evidence_path"] == expected_path
        assert ctx["artifact_registry"][expected_path]["provenance"] == "BASELINE"
        advance(state, ctx)
