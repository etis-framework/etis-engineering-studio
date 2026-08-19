import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docker_build_context_excludes_sensitive_and_local_material():
    dockerignore = ROOT / ".dockerignore"

    assert dockerignore.exists(), "root .dockerignore is required"

    entries = {
        line.strip()
        for line in dockerignore.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    required = {
        ".git",
        ".env",
        ".env.*",
        ".venv",
        "**/__pycache__",
        ".pytest_cache",
        "node_modules",
    }

    missing = required - entries
    assert not missing, f".dockerignore missing required exclusions: {sorted(missing)}"


def test_api_dockerfile_does_not_copy_entire_repository():
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()

    broad_copy = re.search(
        r"(?mi)^\s*COPY\s+\.\s+(?:/app|\.)(?:\s*)$",
        dockerfile,
    )

    assert broad_copy is None, (
        "production API image must copy only explicitly required runtime paths"
    )


def test_api_container_runs_as_non_root_user():
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()

    user_directives = re.findall(
        r"(?mi)^\s*USER\s+([^\s#]+)",
        dockerfile,
    )

    assert user_directives, "production API container must declare a runtime USER"

    runtime_user = user_directives[-1].strip().lower()

    assert runtime_user not in {"root", "0"}, (
        "production API container must not run as root"
    )


def test_api_container_base_image_is_pinned_by_digest():
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()

    from_lines = re.findall(
        r"(?mi)^\s*FROM\s+([^\s]+)",
        dockerfile,
    )

    assert from_lines, "production API Dockerfile must declare a base image"

    for image in from_lines:
        assert "@sha256:" in image, (
            f"production container base image must be pinned by digest: {image}"
        )


def test_production_python_dependencies_are_exactly_pinned():
    requirements = ROOT / "apps/api/requirements.txt"

    mutable = []

    for raw_line in requirements.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith(("-", "git+", "http://", "https://")):
            continue

        if "==" not in line:
            mutable.append(line)

    assert not mutable, (
        "production Python dependencies must use exact == pins: "
        f"{mutable}"
    )



def test_api_container_excludes_dormant_web_scaffold():
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()

    assert "COPY apps /app/apps" not in dockerfile, (
        "production API image must not copy the entire apps tree"
    )

    assert "COPY apps/api /app/apps/api" in dockerfile, (
        "production API image must explicitly copy only the API application"
    )


def test_github_actions_are_pinned_to_full_commit_sha():
    workflow_paths = [
        ROOT / ".github/workflows/ci.yml",
        ROOT / ".github/workflows/deploy-azure.yml",
    ]

    mutable = []

    for workflow in workflow_paths:
        for line in workflow.read_text().splitlines():
            stripped = line.strip()

            if not stripped.startswith("- uses:"):
                continue

            action = stripped.split("uses:", 1)[1].strip()

            # Local repository actions do not require external provenance pins.
            if action.startswith("./"):
                continue

            if "@" not in action:
                mutable.append(f"{workflow.name}: {action}")
                continue

            _, ref = action.rsplit("@", 1)

            if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                mutable.append(f"{workflow.name}: {action}")

    assert not mutable, (
        "external GitHub Actions must be pinned to full commit SHAs: "
        f"{mutable}"
    )


def test_dependabot_covers_production_dependency_ecosystems():
    config_path = ROOT / ".github/dependabot.yml"

    assert config_path.exists(), (
        ".github/dependabot.yml is required to maintain pinned dependencies"
    )

    text = config_path.read_text()

    required_ecosystems = {
        "pip",
        "docker",
        "github-actions",
    }

    configured = set(
        re.findall(
            r'(?m)^\s*-\s*package-ecosystem:\s*["\']?([^"\'\s]+)',
            text,
        )
    )

    missing = required_ecosystems - configured

    assert not missing, (
        "Dependabot must cover all production dependency ecosystems: "
        f"{sorted(missing)}"
    )


def test_ci_python_tooling_is_exactly_pinned():
    requirements = ROOT / "requirements-dev.txt"

    mutable = []

    for raw_line in requirements.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or line.startswith("-r "):
            continue

        if "==" not in line:
            mutable.append(line)

    assert not mutable, (
        "CI/development Python tooling must use exact == pins: "
        f"{mutable}"
    )


def test_ci_does_not_install_unpinned_latest_pip():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert "python -m pip install --upgrade pip" not in workflow, (
        "CI must not upgrade pip to an unpinned latest version"
    )


def test_ci_audits_production_python_dependencies_for_known_vulnerabilities():
    requirements = (ROOT / "requirements-dev.txt").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert re.search(
        r"(?m)^pip-audit==[0-9][^\s]*$",
        requirements,
    ), "CI tooling must include an exactly pinned pip-audit version"

    assert "python -m pip_audit -r apps/api/requirements.lock" in workflow, (
        "CI must audit the production Python dependency set for known vulnerabilities"
    )


def test_ci_generates_and_preserves_production_sbom():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert (
        "python -m pip_audit "
        "-r apps/api/requirements.lock "
        "-f cyclonedx-json "
        "-o artifacts/etis-api-sbom.cdx.json"
    ) in workflow, (
        "CI must generate a CycloneDX SBOM for production Python dependencies"
    )

    assert re.search(
        r"uses:\s*actions/upload-artifact@[0-9a-fA-F]{40}",
        workflow,
    ), "CI must preserve the generated SBOM as a build artifact"

    assert "artifacts/etis-api-sbom.cdx.json" in workflow, (
        "CI artifact upload must include the production SBOM"
    )


def test_ci_postgres_service_image_is_pinned_by_digest():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    match = re.search(
        r"(?m)^\s*image:\s*(postgres:[^\s]+)\s*$",
        workflow,
    )

    assert match, "CI PostgreSQL service image must be declared"

    image = match.group(1)

    assert "@sha256:" in image, (
        f"CI PostgreSQL service image must be pinned by digest: {image}"
    )


def test_ci_builds_production_api_container():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert (
        "docker build -f apps/api/Dockerfile "
        "-t etis-engineering-studio:ci ."
    ) in workflow, (
        "CI must build the production API container on every pull request"
    )


def test_production_python_install_uses_transitive_lockfile():
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()
    lockfile = ROOT / "apps/api/requirements.lock"

    assert lockfile.exists(), (
        "production Python dependencies require a transitive lockfile"
    )

    assert "COPY apps/api/requirements.lock /app/requirements.lock" in dockerfile, (
        "production image must copy the transitive Python lockfile"
    )

    assert (
        "pip install --no-cache-dir --require-hashes "
        "-r /app/requirements.lock"
    ) in dockerfile, (
        "production image must install from the transitive lockfile with hash verification"
    )


def test_ci_security_controls_use_production_lockfile():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert "python -m pip_audit -r apps/api/requirements.lock" in workflow, (
        "CI vulnerability audit must inspect the exact production lockfile"
    )

    assert (
        "python -m pip_audit "
        "-r apps/api/requirements.lock "
        "-f cyclonedx-json "
        "-o artifacts/etis-api-sbom.cdx.json"
    ) in workflow, (
        "production SBOM must be generated from the exact production lockfile"
    )


def test_production_python_lockfile_uses_hash_verification():
    lockfile = (ROOT / "apps/api/requirements.lock").read_text()
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()

    pinned_packages = [
        line
        for line in lockfile.splitlines()
        if line
        and not line.startswith("#")
        and not line.startswith((" ", "\t", "--"))
        and "==" in line
    ]

    hash_count = lockfile.count("--hash=sha256:")

    assert pinned_packages, "production lockfile must contain pinned packages"

    assert hash_count >= len(pinned_packages), (
        "every locked production package must have at least one SHA-256 artifact hash"
    )

    assert (
        "pip install --no-cache-dir --require-hashes -r /app/requirements.lock"
        in dockerfile
    ), "production image must enforce lockfile hashes during installation"

def test_production_container_includes_alembic_migration_scripts():
    dockerfile = (ROOT / "apps/api/Dockerfile").read_text()
    alembic_ini = (ROOT / "alembic.ini").read_text()

    assert "script_location = %(here)s/migrations" in alembic_ini, (
        "Alembic configuration must point to the production migration directory"
    )

    assert "COPY migrations /app/migrations" in dockerfile, (
        "production image must include the Alembic migration scripts required "
        "by fail-closed /ready migration validation"
    )
