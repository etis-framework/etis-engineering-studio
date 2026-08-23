#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/output.sh"
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_repo
etis_require_az_login
etis_require_command python3

overall="PASS"
advisory="PASS"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/etis-acceptance-XXXXXX")"

cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

etis_header "ETIS Engineering Studio" "Production Acceptance"

run_required_check() {
  local command_name="$1"
  local label="$2"
  local output_file="${tmp_dir}/${command_name}.out"

  if "${SCRIPT_DIR}/${command_name}.sh" >"${output_file}" 2>&1; then
    etis_status_row "${label}" "PASS"
    return 0
  fi

  etis_status_row "${label}" "FAIL"
  overall="FAIL"
  return 1
}

run_informational_check() {
  local command_name="$1"
  local label="$2"
  local output_file="${tmp_dir}/${command_name}.out"

  if "${SCRIPT_DIR}/${command_name}.sh" >"${output_file}" 2>&1; then
    if grep -Eq 'COST: WARN|BUDGET: WARN' "${output_file}"; then
      etis_status_row "${label}" "WARN"
      advisory="WARN"
    else
      etis_status_row "${label}" "PASS"
    fi
    return 0
  fi

  etis_status_row "${label}" "WARN" "telemetry unavailable"
  advisory="WARN"
  return 0
}

printf '\n'
etis_section "Required Production Checks"

run_required_check "status" "Production Status" || true
run_required_check "health" "Application Health" || true
run_required_check "replicas" "Replica Capacity" || true
run_required_check "smoke" "External Smoke Test" || true
run_required_check "drift" "Runtime Drift" || true
run_required_check "budget" "Budget Controls" || true

printf '\n'
etis_section "Informational Checks"

run_informational_check "cost" "Cost Telemetry"

failed_required=()

for name in status health replicas smoke drift budget; do
  output_file="${tmp_dir}/${name}.out"

  if [[ -f "${output_file}" ]] \
    && grep -Eq 'STATUS: FAIL|HEALTH: FAIL|REPLICAS: FAIL|SMOKE TEST: FAIL|DRIFT CHECK: FAIL|BUDGET: FAIL' "${output_file}"; then
    failed_required+=("${name}")
  fi
done

if (( ${#failed_required[@]} > 0 )); then
  printf '\n'
  etis_section "Failure Detail"

  for name in "${failed_required[@]}"; do
    output_file="${tmp_dir}/${name}.out"

    printf '\n'
    printf '  %s\n' "${name}"

    grep -E \
      'FAIL|Next Action|Meaning|Impact|expected|actual|missing|could not|unavailable' \
      "${output_file}" \
      | sed 's/^/    /' \
      | tail -20 \
      || true
  done
fi

printf '\n'
etis_section "Acceptance Context"

etis_row "Application" "${ETIS_AZURE_CONTAINER_APP}"
etis_row "Resource Group" "${ETIS_AZURE_RESOURCE_GROUP}"
etis_row "Public URL" "${ETIS_AZURE_PUBLIC_URL}"
etis_row "Subscription" "$(etis_subscription_name)"

latest_revision="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query properties.latestRevisionName \
    -o tsv
)"

etis_row "Latest Revision" "${latest_revision}"

if [[ "${overall}" == "FAIL" ]]; then
  etis_note \
    "Decision" \
    "Production acceptance is NOT complete." \
    "Resolve the failed required checks before treating the deployment as accepted."

  etis_note \
    "Next Action" \
    "Run the failed command directly for the full diagnostic report." \
    "Do not use a live runtime override as a substitute for correcting repository source when drift is involved."
elif [[ "${overall}" == "WARN" ]]; then
  etis_note \
    "Decision" \
    "Required production checks passed." \
    "One or more informational checks are temporarily unavailable or deserve attention."
else
  etis_note \
    "Decision" \
    "All required production checks passed." \
    "The deployed revision matches the accepted production baseline."
fi

etis_final_status "PRODUCTION ACCEPTANCE" "${overall}"

[[ "${overall}" != "FAIL" ]]
