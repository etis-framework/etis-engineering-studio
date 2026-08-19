from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRE_AZURE = ROOT / "docs" / "GATE17_PRE_AZURE_GO_NO_GO.md"
PRODUCTION_ACCEPTANCE = (
    ROOT
    / "docs"
    / "operations"
    / "POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md"
)
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-azure.yml"


def read_lower(path: Path) -> str:
    assert path.exists(), f"required Gate 17 artifact is missing: {path}"
    return path.read_text(encoding="utf-8").lower()


def test_gate17_is_explicitly_pre_azure_and_not_student_go_live():
    text = read_lower(PRE_AZURE)

    required = (
        "gate 17",
        "final pre-azure go/no-go",
        "go",
        "no-go",
        "azure provisioning",
        "authorizes provisioning",
        "does not authorize student access",
        "post-provisioning production acceptance",
    )
    for phrase in required:
        assert phrase in text

    assert text.index("gate 17") < text.index("post-provisioning production acceptance")


def test_gate17_defines_the_pre_azure_blocking_controls():
    text = read_lower(PRE_AZURE)

    required = (
        "all prior gates",
        "ci",
        "production security review",
        "github production environment",
        "environment protection",
        "azure oidc",
        "federated",
        "azure_client_id",
        "azure_tenant_id",
        "azure_subscription_id",
        "azure_resource_group",
        "azure_location",
        "etis_web_origin",
        "entra",
        "github app",
        "github oauth",
        "openai",
        "operations_alert_email",
        "postgres_admin_password",
        "etis_session_secret",
        "budget",
        "cost notification",
        "hostname",
        "callback",
        "operator-configured",
        "blocking",
    )
    for phrase in required:
        assert phrase in text


def test_gate17_requires_evidence_classification_without_claiming_live_azure():
    text = read_lower(PRE_AZURE)

    required = (
        "proven",
        "verified in ci",
        "operator-configured",
        "requires post-provisioning validation",
        "blocked",
        "deferred with explicit acceptance",
        "evidence",
        "owner",
        "rationale",
    )
    for phrase in required:
        assert phrase in text

    assert "live azure controls are not yet verified" in text
    assert "no azure resources have been provisioned" in text


def test_post_provisioning_acceptance_blocks_student_access_until_live_validation():
    text = read_lower(PRODUCTION_ACCEPTANCE)

    required = (
        "post-provisioning production acceptance",
        "student access",
        "explicit go",
        "dns",
        "https",
        "microsoft entra",
        "github oauth",
        "github app",
        "authorized private repository",
        "application insights",
        "log analytics",
        "action group",
        "restartcount",
        "5xx",
        "is_db_alive",
        "storage_percent",
        "/health",
        "/ready",
        "backup",
        "point-in-time restore",
        "separate recovery server",
        "private networking",
        "alembic",
        "rto",
        "rpo",
        "authentication",
        "authorization",
        "rollback",
    )
    for phrase in required:
        assert phrase in text

    assert "a successful deployment is not itself a go-live decision" in text
    assert "a successful `/ready` response is necessary but not sufficient" in text


def test_wave1_acceptance_is_split_between_pre_azure_and_live_acceptance():
    pre = read_lower(PRE_AZURE)
    post = read_lower(PRODUCTION_ACCEPTANCE)

    # Source/CI evidence already established before Azure provisioning.
    for phrase in (
        "a1",
        "a2",
        "strong",
        "mixed",
        "weak",
        "ai can be disabled",
        "provenance",
        "frozen evidence",
        "instructor",
        "automated tests",
    ):
        assert phrase in pre

    # Azure-backed portions of Wave 1 cannot be claimed before resources exist.
    for phrase in (
        "budget",
        "alerts",
        "secrets",
        "https",
        "logging",
        "backups",
        "access controls",
    ):
        assert phrase in post


def test_deployment_workflow_remains_manual_protected_and_oidc_based():
    text = read_lower(DEPLOY_WORKFLOW)

    assert "workflow_dispatch:" in text
    assert "environment: production" in text
    assert "id-token: write" in text
    assert "azure/login@" in text
    assert "client-id:" in text
    assert "tenant-id:" in text
    assert "subscription-id:" in text
    assert "needs: release_gate" in text


def test_gate17_evidence_rules_forbid_secret_material():
    pre = read_lower(PRE_AZURE)
    post = read_lower(PRODUCTION_ACCEPTANCE)

    for text in (pre, post):
        for phrase in (
            "do not record secret values",
            "access token",
            "database password",
            "api key",
            "session cookie",
        ):
            assert phrase in text


def test_gate17_defers_azure_resource_and_rbac_bootstrap_until_after_go():
    text = " ".join(read_lower(PRE_AZURE).split())

    required = (
        "no production azure resource group is created before gate 17 go",
        "zero azure resource authority before gate 17 go",
        "after gate 17 go",
        "create the empty production resource group",
        "contributor",
        "role based access control administrator",
        "acrpush",
        "resource-group scope",
        "no subscription-wide deployment role",
        "then run the production deployment workflow",
    )

    for phrase in required:
        assert phrase in text
