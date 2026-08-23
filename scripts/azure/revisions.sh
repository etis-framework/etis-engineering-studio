#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_az_login
etis_require_container_app

etis_header "ETIS Engineering Studio" "Production Revisions"

revision_json="$(
  az containerapp revision list \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    -o json
)"

latest_revision="$(
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query properties.latestRevisionName \
    -o tsv
)"

etis_section "Revision History"

printf '  %-31s %-8s %-9s %-10s %s\n' \
  "Revision" \
  "Active" \
  "Traffic" \
  "Replicas" \
  "Created"

printf '  %-31s %-8s %-9s %-10s %s\n' \
  "-------------------------------" \
  "--------" \
  "---------" \
  "----------" \
  "-------------------"

ETIS_REVISION_JSON="${revision_json}" \
ETIS_LATEST_REVISION="${latest_revision}" \
python3 - <<PY
import json
import os

latest = os.environ["ETIS_LATEST_REVISION"]
data = json.loads(os.environ["ETIS_REVISION_JSON"])

def created(item):
    props = item.get("properties") or {}
    return props.get("createdTime") or ""

data.sort(key=created, reverse=True)

for item in data:
    name = item.get("name") or "-"
    props = item.get("properties") or {}
    active = "Yes" if props.get("active") else "No"
    traffic = props.get("trafficWeight")
    replicas = props.get("replicas")
    created_time = props.get("createdTime") or "-"
    marker = "*" if name == latest else " "
    traffic_text = f"{traffic}%" if traffic is not None else "-"
    replicas_text = str(replicas) if replicas is not None else "-"
    print(
        f"{marker} {name:<31} {active:<8} {traffic_text:<9} "
        f"{replicas_text:<10} {created_time}"
    )
PY

printf '\n'
etis_row "Current Revision" "${latest_revision}"
printf '  * marks the current latest revision.\n'
