#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/output.sh"
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_az_login
etis_require_container_app

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/azure/etis-azure scale <min-replicas> <max-replicas>

Examples:
  ./scripts/azure/etis-azure scale 1 5
  ./scripts/azure/etis-azure scale 0 5

This command changes LIVE Azure runtime configuration.

It does not modify infra/azure/app.bicep.
Repository infrastructure remains authoritative.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if (( $# != 2 )); then
  usage >&2
  exit 2
fi

requested_min="$1"
requested_max="$2"

if [[ ! "${requested_min}" =~ ^[0-9]+$ ]]; then
  etis_die "Minimum replicas must be a non-negative integer."
fi

if [[ ! "${requested_max}" =~ ^[0-9]+$ ]]; then
  etis_die "Maximum replicas must be a positive integer."
fi

if (( requested_max < 1 )); then
  etis_die "Maximum replicas must be at least 1."
fi

if (( requested_min > requested_max )); then
  etis_die "Minimum replicas cannot exceed maximum replicas."
fi

if (( requested_max > 10 )); then
  etis_die "Maximum replicas above 10 are outside the accepted operational safety boundary."
fi

current_json="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query '{
      minReplicas:properties.template.scale.minReplicas,
      maxReplicas:properties.template.scale.maxReplicas,
      latestRevision:properties.latestRevisionName
    }' \
    -o json
)"

IFS=$'\t' read -r current_min current_max latest_revision < <(
  python3 -c '
import json, sys

d = json.load(sys.stdin)

print("\t".join(str(v) for v in (
    d.get("minReplicas"),
    d.get("maxReplicas"),
    d.get("latestRevision") or "-",
)))
' <<<"${current_json}"
)

etis_header "ETIS Engineering Studio" "Production Scale Override"

etis_section "Target"
etis_row "Environment" "PRODUCTION"
etis_row "Application" "${ETIS_AZURE_CONTAINER_APP}"
etis_row "Resource Group" "${ETIS_AZURE_RESOURCE_GROUP}"
etis_row "Latest Revision" "${latest_revision}"

printf '\n'
etis_section "Scale Configuration"

etis_row "Current Min / Max" "${current_min} / ${current_max}"
etis_row "Requested Min / Max" "${requested_min} / ${requested_max}"

if [[ "${requested_min}" == "${current_min}" \
  && "${requested_max}" == "${current_max}" ]]; then
  printf '\n'
  etis_status_row "Change Required" "PASS" "runtime already matches requested values"

  etis_note \
    "Result" \
    "No Azure change was made."

  etis_final_status "SCALE OVERRIDE" "PASS"
  exit 0
fi

printf '\n'
etis_section "Safety Boundary"

etis_status_row \
  "Runtime Mutation" \
  "WARN" \
  "this will change live production"

etis_row \
  "Bicep Baseline" \
  "${ETIS_EXPECTED_MIN_REPLICAS} / ${ETIS_EXPECTED_MAX_REPLICAS}"

if (( requested_min == 0 )); then
  etis_status_row \
    "Scale-to-Zero" \
    "WARN" \
    "students may experience cold-start latency"

  etis_note \
    "Impact" \
    "A minimum replica count of 0 allows production to scale completely to zero." \
    "This can reintroduce significant first-request startup delay."
fi

etis_note \
  "Important" \
  "This is a LIVE runtime override only." \
  "infra/azure/app.bicep remains authoritative." \
  "A later deployment can overwrite this runtime setting."

printf '\n'
printf 'Type PROD to continue: '
IFS= read -r confirmation

if [[ "${confirmation}" != "PROD" ]]; then
  printf '\n'
  etis_status_row "Production Change" "WARN" "cancelled"
  etis_final_status "SCALE OVERRIDE" "WARN"
  exit 0
fi

printf '\n'
etis_section "Applying Change"

az containerapp update \
  --name "${ETIS_AZURE_CONTAINER_APP}" \
  --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
  --min-replicas "${requested_min}" \
  --max-replicas "${requested_max}" \
  --only-show-errors \
  --output none

verification_json="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query '{
      minReplicas:properties.template.scale.minReplicas,
      maxReplicas:properties.template.scale.maxReplicas
    }' \
    -o json
)"

IFS=$'\t' read -r verified_min verified_max < <(
  python3 -c '
import json, sys

d = json.load(sys.stdin)

print("\t".join(str(v) for v in (
    d.get("minReplicas"),
    d.get("maxReplicas"),
)))
' <<<"${verification_json}"
)

if [[ "${verified_min}" == "${requested_min}" \
  && "${verified_max}" == "${requested_max}" ]]; then
  etis_status_row \
    "Azure Runtime" \
    "PASS" \
    "${verified_min} / ${verified_max}"
else
  etis_status_row \
    "Azure Runtime" \
    "FAIL" \
    "requested ${requested_min}/${requested_max}, actual ${verified_min}/${verified_max}"

  etis_final_status "SCALE OVERRIDE" "FAIL"
  exit 1
fi

if [[ "${verified_min}" != "${ETIS_EXPECTED_MIN_REPLICAS}" \
  || "${verified_max}" != "${ETIS_EXPECTED_MAX_REPLICAS}" ]]; then
  etis_note \
    "Configuration Drift" \
    "Live runtime now differs from the accepted production baseline." \
    "Run ./scripts/azure/etis-azure drift to see the resulting drift."
else
  etis_note \
    "Configuration" \
    "Live runtime matches the accepted production scaling baseline."
fi

etis_final_status "SCALE OVERRIDE" "PASS"
