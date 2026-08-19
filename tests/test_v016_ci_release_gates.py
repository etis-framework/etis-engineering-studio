import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
DEPLOY = ROOT / ".github/workflows/deploy-azure.yml"


def _text(path: Path) -> str:
    assert path.exists(), f"Required workflow is missing: {path}"
    return path.read_text()


def test_ci_has_explicit_postgresql_migration_release_gate():
    workflow = _text(CI)

    assert re.search(
        r"(?mi)^\s*-\s+name:\s+Validate production database migrations\s*$",
        workflow,
    ), (
        "CI must expose PostgreSQL/Alembic correctness as an explicit "
        "release gate rather than relying only on the aggregate pytest run"
    )

    assert (
        "python -m pytest -q tests/test_v016_database_migrations.py"
        in workflow
    ), (
        "the explicit migration gate must run the production migration "
        "contract against the CI PostgreSQL service"
    )


def test_ci_runs_production_container_smoke_test_against_ready_endpoint():
    workflow = _text(CI)

    assert re.search(
        r"(?mi)^\s*-\s+name:\s+Smoke test production API container\s*$",
        workflow,
    ), "CI must explicitly smoke-test the built production container"

    required_fragments = {
        "docker run",
        "--network host",
        "ETIS_ENV=production",
        "ETIS_DATABASE_URL=",
        "ETIS_DEV_LOGIN=false",
        "ETIS_WEB_ORIGIN=https://",
        "ETIS_SESSION_SECRET=",
        "ENTRA_CLIENT_ID=",
        "ENTRA_CLIENT_SECRET=",
        "ENTRA_TENANT=",
        "GITHUB_APP_ID=",
        "GITHUB_APP_PRIVATE_KEY=",
        "GITHUB_OAUTH_CLIENT_ID=",
        "GITHUB_OAUTH_CLIENT_SECRET=",
        "OPENAI_API_KEY=",
        "etis-engineering-studio:ci",
        "http://127.0.0.1:8000/ready",
    }

    missing = sorted(
        fragment
        for fragment in required_fragments
        if fragment not in workflow
    )

    assert not missing, (
        "production container smoke test is incomplete; missing: "
        f"{missing}"
    )


def test_ci_container_smoke_gate_verifies_ready_payload_not_only_http_startup():
    workflow = _text(CI)

    assert '"status":"ready"' in workflow or "'\"status\":\"ready\"'" in workflow, (
        "container smoke gate must prove /ready reports application readiness, "
        "not merely that a TCP listener started"
    )

    assert "migration_current" in workflow, (
        "container smoke gate must verify the running production container "
        "sees the database at current Alembic head"
    )


def test_ci_container_smoke_gate_always_removes_test_container():
    workflow = _text(CI)

    assert (
        "docker rm -f etis-api-smoke" in workflow
        or "docker stop etis-api-smoke" in workflow
    ), (
        "CI must clean up the production smoke-test container even when the "
        "readiness assertion fails"
    )


def test_manual_azure_deploy_has_release_gate_before_azure_authority():
    workflow = _text(DEPLOY)

    assert re.search(
        r"(?m)^\s{2}release_gate:\s*$",
        workflow,
    ), (
        "manual deployment requires a release_gate job for the exact "
        "workflow-dispatched commit"
    )

    assert re.search(
        r"(?m)^\s{4}needs:\s+release_gate\s*$",
        workflow,
    ), (
        "the Azure deployment job must depend on successful release_gate"
    )

    deploy_position = workflow.find("  deploy:")
    gate_position = workflow.find("  release_gate:")

    assert gate_position != -1 and deploy_position != -1
    assert gate_position < deploy_position, (
        "release_gate must be defined before the Azure deployment job"
    )


def test_manual_deploy_release_gate_revalidates_exact_selected_commit():
    workflow = _text(DEPLOY)

    release_gate_start = workflow.index("  release_gate:")
    deploy_start = workflow.index("  deploy:")
    release_gate = workflow[release_gate_start:deploy_start]

    required_fragments = {
        "actions/checkout@",
        "actions/setup-python@",
        "python -m pip install -r requirements-dev.txt",
        "python -m pytest -q",
        "python scripts/validate_course_model.py",
        "docker build -f apps/api/Dockerfile",
    }

    missing = sorted(
        fragment
        for fragment in required_fragments
        if fragment not in release_gate
    )

    assert not missing, (
        "manual deployment release gate must revalidate the exact selected "
        f"commit before Azure authority is acquired; missing: {missing}"
    )


def test_azure_login_occurs_only_in_deploy_job_after_release_gate():
    workflow = _text(DEPLOY)

    release_gate_start = workflow.index("  release_gate:")
    deploy_start = workflow.index("  deploy:")

    release_gate = workflow[release_gate_start:deploy_start]
    deploy = workflow[deploy_start:]

    assert "azure/login@" not in release_gate, (
        "release validation must not require Azure authority"
    )

    assert "azure/login@" in deploy, (
        "Azure OIDC login belongs only in the gated deployment job"
    )
