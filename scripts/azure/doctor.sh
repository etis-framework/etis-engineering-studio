#!/usr/bin/env bash
set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

failures=0
warnings=0

etis_header "ETIS Engineering Studio" "Local Azure Operations Doctor"

etis_section "Local Environment"

if etis_command_exists az; then
  etis_status_row "Azure CLI" "PASS" "$(az version --query '"azure-cli"' -o tsv 2>/dev/null || printf 'installed')"
else
  etis_status_row "Azure CLI" "FAIL" "not installed"
  failures=$((failures + 1))
fi

if etis_command_exists git; then
  etis_status_row "Git" "PASS" "$(git --version | sed 's/^git version //')"
else
  etis_status_row "Git" "FAIL" "not installed"
  failures=$((failures + 1))
fi

if etis_command_exists curl; then
  etis_status_row "curl" "PASS" "available"
else
  etis_status_row "curl" "FAIL" "not installed"
  failures=$((failures + 1))
fi

if [[ -f "${ETIS_REPO_ROOT}/infra/azure/app.bicep" ]]; then
  etis_status_row "Repository" "PASS" "$(basename "${ETIS_REPO_ROOT}")"
else
  etis_status_row "Repository" "FAIL" "not detected"
  failures=$((failures + 1))
fi

git_branch="$(
  git -C "${ETIS_REPO_ROOT}" branch --show-current 2>/dev/null || true
)"
etis_row "Git Branch" "${git_branch:-detached HEAD}"

if [[ -z "$(git -C "${ETIS_REPO_ROOT}" status --porcelain 2>/dev/null)" ]]; then
  etis_status_row "Git Working Tree" "PASS" "clean"
else
  etis_status_row "Git Working Tree" "WARN" "changes present"
  warnings=$((warnings + 1))
fi

printf '\n'
etis_section "Azure Access"

if etis_command_exists az && az account show >/dev/null 2>&1; then
  etis_status_row "Azure Authentication" "PASS" "authenticated"
  etis_row "Subscription" "$(etis_subscription_name)"

  if etis_container_app_exists; then
    etis_status_row "Production Container App" "PASS" "${ETIS_AZURE_CONTAINER_APP}"
  else
    etis_status_row "Production Container App" "FAIL" "not found"
    failures=$((failures + 1))
  fi
else
  etis_status_row "Azure authentication" "FAIL" "run: az login"
  failures=$((failures + 1))
fi

printf '\n'
etis_section "Source Baseline"

bicep_min="$(etis_bicep_default minReplicas 2>/dev/null || true)"
bicep_max="$(etis_bicep_default maxReplicas 2>/dev/null || true)"

if [[ "${bicep_min}" == "${ETIS_EXPECTED_MIN_REPLICAS}" ]]; then
  etis_status_row "Bicep minimum replicas" "PASS" "${bicep_min}"
else
  etis_status_row \
    "Bicep minimum replicas" \
    "FAIL" \
    "expected ${ETIS_EXPECTED_MIN_REPLICAS}, source ${bicep_min:-unknown}"
  failures=$((failures + 1))
fi

if [[ "${bicep_max}" == "${ETIS_EXPECTED_MAX_REPLICAS}" ]]; then
  etis_status_row "Bicep maximum replicas" "PASS" "${bicep_max}"
else
  etis_status_row \
    "Bicep maximum replicas" \
    "FAIL" \
    "expected ${ETIS_EXPECTED_MAX_REPLICAS}, source ${bicep_max:-unknown}"
  failures=$((failures + 1))
fi

if (( failures > 0 )); then
  etis_final_status "LOCAL OPERATIONS READINESS" "FAIL"
  exit 1
fi

if (( warnings > 0 )); then
  etis_final_status "LOCAL OPERATIONS READINESS" "WARN"
  exit 0
fi

etis_final_status "LOCAL OPERATIONS READINESS" "PASS"
