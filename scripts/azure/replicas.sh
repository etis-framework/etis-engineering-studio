#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_az_login
etis_require_container_app

etis_header "ETIS Engineering Studio" "Production Replicas"

scale_json="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query '{
      latestRevision:properties.latestRevisionName,
      minReplicas:properties.template.scale.minReplicas,
      maxReplicas:properties.template.scale.maxReplicas
    }' \
    -o json
)"

IFS=$'\t' read -r latest_revision min_replicas max_replicas < <(
  python3 -c '
import json, sys
d=json.load(sys.stdin)
print("\t".join(str(v) for v in (
    d.get("latestRevision") or "-",
    d.get("minReplicas") if d.get("minReplicas") is not None else "-",
    d.get("maxReplicas") if d.get("maxReplicas") is not None else "-"
)))
' <<<"${scale_json}"
)

replica_json="$(
  az containerapp replica list \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    -o json
)"

running_count="$(
  python3 -c '
import json, sys
data=json.load(sys.stdin)
print(len(data))
' <<<"${replica_json}"
)"

overall="PASS"

etis_section "Configured Capacity"

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

etis_row "Latest Revision" "${latest_revision}"

printf '\n'
etis_section "Running Capacity"

if [[ "${running_count}" =~ ^[0-9]+$ ]] \
  && (( running_count >= ETIS_EXPECTED_MIN_REPLICAS )); then
  etis_status_row "Running Replicas" "PASS" "${running_count}"
else
  etis_status_row \
    "Running Replicas" \
    "FAIL" \
    "expected >=${ETIS_EXPECTED_MIN_REPLICAS}, actual ${running_count}"
  overall="FAIL"
fi

if (( running_count > 0 )); then
  printf '\n'
  printf '  %-43s %-28s %-7s %-8s %s\n' \
    "Replica" \
    "Revision" \
    "Ready" \
    "Restarts" \
    "State"

  printf '  %-43s %-28s %-7s %-8s %s\n' \
    "-------------------------------------------" \
    "----------------------------" \
    "-------" \
    "--------" \
    "-------"

  python3 -c '
import json
import sys

data = json.load(sys.stdin)

for item in data:
    name = item.get("name") or "-"
    resource_id = item.get("id") or ""
    props = item.get("properties") or {}
    containers = props.get("containers") or []

    revision = "-"
    marker = "/revisions/"
    if marker in resource_id:
        revision = resource_id.split(marker, 1)[1].split("/", 1)[0]

    state = props.get("runningState") or "-"
    ready = "-"
    restarts = "-"

    if containers:
        container = containers[0]
        ready_value = container.get("ready")
        if ready_value is True:
            ready = "Yes"
        elif ready_value is False:
            ready = "No"

        restart_value = container.get("restartCount")
        if restart_value is not None:
            restarts = str(restart_value)

        state = container.get("runningState") or state

    print(
        f"  {name:<43} "
        f"{revision:<28} "
        f"{ready:<7} "
        f"{restarts:<8} "
        f"{state}"
    )
' <<<"${replica_json}"
fi

etis_final_status "REPLICAS" "${overall}"

[[ "${overall}" != "FAIL" ]]
