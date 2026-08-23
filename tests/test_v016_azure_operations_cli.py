from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
AZURE_DIR = ROOT / "scripts" / "azure"
CLI = AZURE_DIR / "etis-azure"


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_azure_operations_shell_scripts_have_valid_bash_syntax():
    scripts = sorted(AZURE_DIR.glob("*.sh")) + [CLI]

    assert scripts

    for script in scripts:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, (
            f"{script.relative_to(ROOT)} failed bash syntax validation:\n"
            f"{result.stderr}"
        )


def test_azure_operations_help_lists_all_implemented_commands():
    result = run_command("help")

    assert result.returncode == 0

    output = result.stdout

    expected_commands = (
        "doctor",
        "status",
        "config",
        "health",
        "replicas",
        "revisions",
        "logs",
        "cost",
        "budget",
        "smoke",
        "drift",
        "acceptance",
        "scale",
    )

    for command in expected_commands:
        assert command in output

    assert "logs --tail N" in output
    assert "logs --all" in output
    assert "logs --raw" in output
    assert "logs --follow" in output
    assert "scale <min-replicas> <max-replicas>" in output


def test_azure_operations_cli_has_no_local_deploy_command():
    result = run_command("deploy")

    assert result.returncode == 2
    assert "Unknown command: deploy" in result.stderr


def test_logs_command_has_command_specific_help():
    result = run_command("logs", "--help")

    assert result.returncode == 0
    assert "--tail N" in result.stdout
    assert "--all" in result.stdout
    assert "--raw" in result.stdout
    assert "--follow" in result.stdout


def test_scale_command_has_command_specific_help():
    result = run_command("scale", "--help")

    assert result.returncode == 0
    assert "scale <min-replicas> <max-replicas>" in result.stdout
    assert "LIVE Azure runtime configuration" in result.stdout
    assert "Repository infrastructure remains authoritative" in result.stdout


def test_scale_rejects_invalid_arguments_before_azure_mutation():
    result = run_command("scale", "5", "1")

    assert result.returncode != 0
    assert "Minimum replicas cannot exceed maximum replicas" in result.stderr


def test_production_baseline_constants_are_explicit():
    common = (AZURE_DIR / "lib" / "common.sh").read_text(encoding="utf-8")
    drift = (AZURE_DIR / "drift.sh").read_text(encoding="utf-8")

    assert 'ETIS_EXPECTED_MIN_REPLICAS="${ETIS_EXPECTED_MIN_REPLICAS:-1}"' in common
    assert 'ETIS_EXPECTED_MAX_REPLICAS="${ETIS_EXPECTED_MAX_REPLICAS:-5}"' in common
    assert 'ETIS_EXPECTED_REVISION_MODE="${ETIS_EXPECTED_REVISION_MODE:-Single}"' in common
    assert 'if [[ "${runtime_port}" == "8000" ]]' in drift


def test_smoke_requires_native_fail_closed_shell():
    smoke = (AZURE_DIR / "smoke.sh").read_text(encoding="utf-8")

    assert '<div id="appShell" class="shell hidden" hidden>' in smoke
    assert "native fail-closed protection present" in smoke


def test_acceptance_keeps_cost_telemetry_informational():
    acceptance = (AZURE_DIR / "acceptance.sh").read_text(encoding="utf-8")

    required_section = acceptance.split(
        'etis_section "Required Production Checks"',
        1,
    )[1].split(
        'etis_section "Informational Checks"',
        1,
    )[0]

    informational_section = acceptance.split(
        'etis_section "Informational Checks"',
        1,
    )[1]

    assert 'run_required_check "budget" "Budget Controls"' in required_section
    assert 'run_informational_check "cost" "Cost Telemetry"' in informational_section
    assert 'overall="FAIL"' not in informational_section.split(
        'failed_required=()',
        1,
    )[0]


def test_operations_cli_documents_deployment_boundary():
    help_result = run_command("help")

    assert help_result.returncode == 0
    assert "Production deployment is intentionally NOT provided here." in help_result.stdout
    assert "branch -> PR -> CI -> merge -> GitHub Deploy Azure workflow" in help_result.stdout
