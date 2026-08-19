from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OPERATIONS_IAC = ROOT / "infra" / "azure" / "operations.bicep"
CI = ROOT / ".github" / "workflows" / "ci.yml"
DEPLOY = ROOT / ".github" / "workflows" / "deploy-azure.yml"

BACKUP_DRILL = ROOT / "scripts" / "verify_postgres_backup_restore.sh"

OPERATIONS_RUNBOOK = ROOT / "docs" / "operations" / "PRODUCTION_OPERATIONS_RUNBOOK.md"
INCIDENT_RUNBOOK = ROOT / "docs" / "operations" / "INCIDENT_RESPONSE_RUNBOOK.md"
RECOVERY_RUNBOOK = ROOT / "docs" / "operations" / "DATABASE_RECOVERY_RUNBOOK.md"
OPERATIONS_INDEX = ROOT / "docs" / "operations" / "README.md"

INFRA_README = ROOT / "infra" / "azure" / "README.md"


def read_required(path: Path) -> str:
    assert path.exists(), f"required Gate 16 artifact is missing: {path.relative_to(ROOT)}"
    return path.read_text()


def require_all(text: str, tokens: list[str]) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, f"missing required Gate 16 contract elements: {missing}"


def test_operations_iac_defines_actionable_runtime_and_database_alerts():
    text = read_required(OPERATIONS_IAC)

    require_all(
        text,
        [
            "Microsoft.Insights/actionGroups@",
            "emailReceivers",
            "Microsoft.Insights/metricAlerts@",
            "RestartCount",
            "Requests",
            "statusCodeCategory",
            "5xx",
            "is_db_alive",
            "storage_percent",
        ],
    )


def test_operations_alerts_do_not_treat_expected_scale_to_zero_as_an_outage():
    text = read_required(OPERATIONS_IAC)

    assert "Replicas" not in text, (
        "production currently permits minReplicas=0; replica-count alerts would "
        "mistake intentional scale-to-zero behavior for an outage"
    )


def test_deployment_reconciles_operations_after_application_before_final_readiness():
    text = read_required(DEPLOY)

    require_all(
        text,
        [
            "OPERATIONS_ALERT_EMAIL",
            "infra/azure/app.bicep",
            "infra/azure/operations.bicep",
            "Verify production readiness",
        ],
    )

    application = text.index("infra/azure/app.bicep")
    operations = text.index("infra/azure/operations.bicep")
    readiness = text.index("Verify production readiness")

    assert application < operations < readiness, (
        "deployment order must be application -> operational controls "
        "-> final readiness verification"
    )


def test_ci_runs_real_postgresql_logical_backup_restore_drill():
    script = read_required(BACKUP_DRILL)
    ci = read_required(CI)

    require_all(
        script,
        [
            "pg_dump",
            "pg_restore",
            "alembic",
            "upgrade",
            "head",
            "alembic_version",
            "backup",
            "restore",
        ],
    )

    assert "scripts/verify_postgres_backup_restore.sh" in ci, (
        "CI must execute the PostgreSQL backup/restore drill"
    )



def test_ci_compiles_gate16_operations_bicep():
    text = read_required(CI)

    assert (
        "az bicep build --file infra/azure/operations.bicep"
        in text
    ), (
        "CI must compile the Gate 16 operational-monitoring Bicep "
        "before production deployment"
    )


def test_production_operations_runbook_defines_monitoring_and_recovery_objectives():
    text = read_required(OPERATIONS_RUNBOOK).lower()

    require_all(
        text,
        [
            "/health",
            "/ready",
            "application insights",
            "log analytics",
            "restartcount",
            "5xx",
            "is_db_alive",
            "storage_percent",
            "rto",
            "rpo",
            "not an sla",
            "escalation",
            "maintenance",
            "security_and_privacy.md",
        ],
    )


def test_incident_runbook_preserves_evidence_and_fail_closed_authority():
    text = read_required(INCIDENT_RUNBOOK).lower()

    require_all(
        text,
        [
            "severity",
            "containment",
            "assessment",
            "recovery",
            "communication",
            "evidence preservation",
            "credentials",
            "key vault",
            "student",
            "post-incident",
            "fail closed",
        ],
    )


def test_database_recovery_runbook_requires_restore_to_new_server_and_validation():
    text = read_required(RECOVERY_RUNBOOK).lower()

    require_all(
        text,
        [
            "point-in-time restore",
            "new server",
            "restore point",
            "private",
            "alembic",
            "/ready",
            "validation",
            "key vault",
            "rollback",
            "rto",
            "rpo",
        ],
    )

    assert "overwrite the source server" not in text, (
        "recovery guidance must preserve the original database while "
        "the restored server is validated"
    )


def test_operations_index_marks_live_azure_restore_drill_as_post_provisioning_evidence():
    text = read_required(OPERATIONS_INDEX).lower()

    require_all(
        text,
        [
            "gate 16",
            "pre-deployment",
            "post-provisioning",
            "point-in-time restore",
            "evidence",
            "gate 17",
        ],
    )


def test_azure_infrastructure_readme_no_longer_describes_gate15_as_only_a_starter():
    text = read_required(INFRA_README).lower()

    assert "azure infrastructure starter" not in text
    assert "production hardening should move postgresql" not in text

    require_all(
        text,
        [
            "main.bicep",
            "secrets.bicep",
            "migration.bicep",
            "app.bicep",
            "operations.bicep",
        ],
    )
