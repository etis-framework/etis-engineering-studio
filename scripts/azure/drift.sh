#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/output.sh"
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_repo
etis_require_az_login
etis_require_container_app
etis_require_command python3
etis_require_command curl

overall="PASS"

etis_header "ETIS Engineering Studio" "Production Drift Check"

runtime_json="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query '{
      name:name,
      resourceGroup:resourceGroup,
      revisionMode:properties.configuration.activeRevisionsMode,
      externalIngress:properties.configuration.ingress.external,
      targetPort:properties.configuration.ingress.targetPort,
      minReplicas:properties.template.scale.minReplicas,
      maxReplicas:properties.template.scale.maxReplicas,
      latestRevision:properties.latestRevisionName
    }' \
    -o json
)"

IFS=$'\t' read -r \
  runtime_name \
  runtime_group \
  runtime_revision_mode \
  runtime_external \
  runtime_port \
  runtime_min \
  runtime_max \
  runtime_revision \
  < <(
    python3 -c '
import json, sys

d = json.load(sys.stdin)

values = (
    d.get("name") or "-",
    d.get("resourceGroup") or "-",
    d.get("revisionMode") or "-",
    str(d.get("externalIngress")).lower(),
    d.get("targetPort") if d.get("targetPort") is not None else "-",
    d.get("minReplicas") if d.get("minReplicas") is not None else "-",
    d.get("maxReplicas") if d.get("maxReplicas") is not None else "-",
    d.get("latestRevision") or "-",
)

print("\t".join(str(value) for value in values))
' <<<"${runtime_json}"
  )

source_min="$(etis_bicep_default minReplicas)"
source_max="$(etis_bicep_default maxReplicas)"

traffic="$(
  az containerapp revision list \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query "[?name=='${runtime_revision}'].properties.trafficWeight | [0]" \
    -o tsv
)"

traffic="${traffic:-0}"

root_file="$(mktemp "${TMPDIR:-/tmp}/etis-drift-root-XXXXXX")"

cleanup() {
  rm -f "${root_file}"
}
trap cleanup EXIT

if ! curl \
    --silent \
    --show-error \
    --fail \
    --max-time 15 \
    "${ETIS_AZURE_PUBLIC_URL}/" \
    > "${root_file}"; then
  root_available=false
else
  root_available=true
fi

printf '\n'
etis_section "Production Target"

if [[ "${runtime_name}" == "${ETIS_AZURE_CONTAINER_APP}" ]]; then
  etis_status_row "Application" "PASS" "${runtime_name}"
else
  etis_status_row \
    "Application" \
    "FAIL" \
    "expected ${ETIS_AZURE_CONTAINER_APP}, actual ${runtime_name}"
  overall="FAIL"
fi

if [[ "${runtime_group}" == "${ETIS_AZURE_RESOURCE_GROUP}" ]]; then
  etis_status_row "Resource Group" "PASS" "${runtime_group}"
else
  etis_status_row \
    "Resource Group" \
    "FAIL" \
    "expected ${ETIS_AZURE_RESOURCE_GROUP}, actual ${runtime_group}"
  overall="FAIL"
fi

etis_row "Latest Revision" "${runtime_revision}"

printf '\n'
etis_section "Source vs Runtime"

if [[ "${source_min}" == "${ETIS_EXPECTED_MIN_REPLICAS}" ]]; then
  etis_status_row "Bicep Minimum Replicas" "PASS" "${source_min}"
else
  etis_status_row \
    "Bicep Minimum Replicas" \
    "FAIL" \
    "accepted ${ETIS_EXPECTED_MIN_REPLICAS}, source ${source_min:-unknown}"
  overall="FAIL"
fi

if [[ "${runtime_min}" == "${source_min}" ]]; then
  etis_status_row "Runtime Minimum Replicas" "PASS" "${runtime_min}"
else
  etis_status_row \
    "Runtime Minimum Replicas" \
    "FAIL" \
    "source ${source_min:-unknown}, runtime ${runtime_min}"
  overall="FAIL"
fi

if [[ "${source_max}" == "${ETIS_EXPECTED_MAX_REPLICAS}" ]]; then
  etis_status_row "Bicep Maximum Replicas" "PASS" "${source_max}"
else
  etis_status_row \
    "Bicep Maximum Replicas" \
    "FAIL" \
    "accepted ${ETIS_EXPECTED_MAX_REPLICAS}, source ${source_max:-unknown}"
  overall="FAIL"
fi

if [[ "${runtime_max}" == "${source_max}" ]]; then
  etis_status_row "Runtime Maximum Replicas" "PASS" "${runtime_max}"
else
  etis_status_row \
    "Runtime Maximum Replicas" \
    "FAIL" \
    "source ${source_max:-unknown}, runtime ${runtime_max}"
  overall="FAIL"
fi

printf '\n'
etis_section "Runtime Invariants"

if [[ "${runtime_revision_mode}" == "${ETIS_EXPECTED_REVISION_MODE}" ]]; then
  etis_status_row "Revision Mode" "PASS" "${runtime_revision_mode}"
else
  etis_status_row \
    "Revision Mode" \
    "FAIL" \
    "expected ${ETIS_EXPECTED_REVISION_MODE}, actual ${runtime_revision_mode}"
  overall="FAIL"
fi

if [[ "${runtime_external}" == "true" ]]; then
  etis_status_row "External Ingress" "PASS" "enabled"
else
  etis_status_row "External Ingress" "FAIL" "${runtime_external}"
  overall="FAIL"
fi

if [[ "${runtime_port}" == "8000" ]]; then
  etis_status_row "Target Port" "PASS" "${runtime_port}"
else
  etis_status_row \
    "Target Port" \
    "FAIL" \
    "expected 8000, actual ${runtime_port}"
  overall="FAIL"
fi

if [[ "${traffic}" == "100" ]]; then
  etis_status_row "Latest Revision Traffic" "PASS" "100%"
else
  etis_status_row \
    "Latest Revision Traffic" \
    "FAIL" \
    "${traffic}%"
  overall="FAIL"
fi

printf '\n'
etis_section "Production UI Boundary"

if [[ "${root_available}" == true ]]; then
  if grep -Fq '<div id="appShell" class="shell hidden" hidden>' "${root_file}"; then
    etis_status_row \
      "Native Fail-Closed Shell" \
      "PASS" \
      "present"
  else
    etis_status_row \
      "Native Fail-Closed Shell" \
      "FAIL" \
      "production markup does not match accepted protection"
    overall="FAIL"
  fi
else
  etis_status_row \
    "Production Root" \
    "FAIL" \
    "could not retrieve public root page"
  overall="FAIL"
fi

if [[ "${overall}" == "FAIL" ]]; then
  etis_note \
    "Meaning" \
    "Live production differs from the accepted or repository-defined baseline." \
    "Treat repository infrastructure as authoritative unless an emergency override is intentional."

  etis_note \
    "Next Action" \
    "Review ./scripts/azure/etis-azure status and config." \
    "Compare the live setting with infra/azure/app.bicep before changing production."
else
  etis_note \
    "Meaning" \
    "No material drift was detected in the checked production invariants." \
    "Live Azure state matches the accepted repository baseline."
fi

etis_final_status "DRIFT CHECK" "${overall}"

[[ "${overall}" != "FAIL" ]]
