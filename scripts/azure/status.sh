#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_repo
etis_require_az_login
etis_require_container_app

app_json="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query '{
      location:location,
      provisioningState:properties.provisioningState,
      revisionMode:properties.configuration.activeRevisionsMode,
      latestRevision:properties.latestRevisionName,
      minReplicas:properties.template.scale.minReplicas,
      maxReplicas:properties.template.scale.maxReplicas,
      fqdn:properties.configuration.ingress.fqdn
    }' \
    -o json
)"

IFS=$'\t' read -r \
  location \
  provisioning \
  revision_mode \
  latest_revision \
  min_replicas \
  max_replicas \
  fqdn \
  < <(
    python3 -c '
import json, sys

d = json.load(sys.stdin)

values = (
    d.get("location") or "-",
    d.get("provisioningState") or "-",
    d.get("revisionMode") or "-",
    d.get("latestRevision") or "-",
    d.get("minReplicas") if d.get("minReplicas") is not None else "-",
    d.get("maxReplicas") if d.get("maxReplicas") is not None else "-",
    d.get("fqdn") or "-",
)

print("\t".join(str(value) for value in values))
' <<<"${app_json}"
  )

running_replicas="$(
  az containerapp replica list \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query 'length(@)' \
    -o tsv
)"

traffic="$(
  az containerapp revision list \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query "[?name=='${latest_revision}'].properties.trafficWeight | [0]" \
    -o tsv
)"

traffic="${traffic:-0}"

overall="PASS"

etis_header "ETIS Engineering Studio" "Production Status"

etis_section "Target"
etis_row "Environment" "PRODUCTION"
etis_row "Application" "${ETIS_AZURE_CONTAINER_APP}"
etis_row "Resource Group" "${ETIS_AZURE_RESOURCE_GROUP}"
etis_row "Region" "${location}"
etis_row "Public URL" "${ETIS_AZURE_PUBLIC_URL}"
etis_row "Azure FQDN" "${fqdn}"
etis_row "Subscription" "$(etis_subscription_name)"

printf '\n'
etis_section "Deployment"

if [[ "${provisioning}" == "Succeeded" ]]; then
  etis_status_row "Provisioning State" "PASS" "${provisioning}"
else
  etis_status_row "Provisioning State" "FAIL" "${provisioning}"
  overall="FAIL"
fi

etis_row "Latest Revision" "${latest_revision}"

if [[ "${revision_mode}" == "${ETIS_EXPECTED_REVISION_MODE}" ]]; then
  etis_status_row "Revision Mode" "PASS" "${revision_mode}"
else
  etis_status_row \
    "Revision Mode" \
    "WARN" \
    "expected ${ETIS_EXPECTED_REVISION_MODE}, actual ${revision_mode}"
  [[ "${overall}" == "PASS" ]] && overall="WARN"
fi

if [[ "${traffic}" == "100" ]]; then
  etis_status_row "Latest Revision Traffic" "PASS" "100%"
else
  etis_status_row "Latest Revision Traffic" "WARN" "${traffic}%"
  [[ "${overall}" == "PASS" ]] && overall="WARN"
fi

printf '\n'
etis_section "Capacity"

if [[ "${min_replicas}" == "${ETIS_EXPECTED_MIN_REPLICAS}" ]]; then
  etis_status_row "Minimum Replicas" "PASS" "${min_replicas}"
else
  etis_status_row \
    "Minimum Replicas" \
    "FAIL" \
    "expected ${ETIS_EXPECTED_MIN_REPLICAS}, actual ${min_replicas}"
  overall="FAIL"
fi

if [[ "${max_replicas}" == "${ETIS_EXPECTED_MAX_REPLICAS}" ]]; then
  etis_status_row "Maximum Replicas" "PASS" "${max_replicas}"
else
  etis_status_row \
    "Maximum Replicas" \
    "WARN" \
    "expected ${ETIS_EXPECTED_MAX_REPLICAS}, actual ${max_replicas}"
  [[ "${overall}" == "PASS" ]] && overall="WARN"
fi

if [[ "${running_replicas}" =~ ^[0-9]+$ ]] \
  && (( running_replicas >= ETIS_EXPECTED_MIN_REPLICAS )); then
  etis_status_row "Running Replicas" "PASS" "${running_replicas}"
else
  etis_status_row \
    "Running Replicas" \
    "FAIL" \
    "expected >=${ETIS_EXPECTED_MIN_REPLICAS}, actual ${running_replicas:-unknown}"
  overall="FAIL"
fi

if [[ "${min_replicas}" == "0" ]]; then
  etis_note \
    "Impact" \
    "Production can scale completely to zero." \
    "Students may experience a significant first-request cold start."

  etis_note \
    "Next Action" \
    "Review infra/azure/app.bicep and the most recent deployment." \
    "Do not treat a live CLI override as the authoritative fix."
fi

etis_final_status "STATUS" "${overall}"

[[ "${overall}" != "FAIL" ]]
