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
      revisionMode:properties.configuration.activeRevisionsMode,
      minReplicas:properties.template.scale.minReplicas,
      maxReplicas:properties.template.scale.maxReplicas,
      fqdn:properties.configuration.ingress.fqdn,
      external:properties.configuration.ingress.external,
      targetPort:properties.configuration.ingress.targetPort,
      cpu:properties.template.containers[0].resources.cpu,
      memory:properties.template.containers[0].resources.memory
    }' \
    -o json
)"

python_values="$(
  python3 -c '
import json, sys
d=json.load(sys.stdin)
keys=("location","revisionMode","minReplicas","maxReplicas","fqdn","external","targetPort","cpu","memory")
for k in keys:
    v=d.get(k)
    print("" if v is None else v)
' <<<"${app_json}"
)"

mapfile_cmd_available=false
if builtin help mapfile >/dev/null 2>&1; then
  mapfile_cmd_available=true
fi

if [[ "${mapfile_cmd_available}" == true ]]; then
  mapfile -t values <<<"${python_values}"
else
  values=()
  while IFS= read -r line; do
    values+=("${line}")
  done <<<"${python_values}"
fi

location="${values[0]:-}"
revision_mode="${values[1]:-}"
min_replicas="${values[2]:-}"
max_replicas="${values[3]:-}"
fqdn="${values[4]:-}"
external="${values[5]:-}"
target_port="${values[6]:-}"
cpu="${values[7]:-}"
memory="${values[8]:-}"

bicep_min="$(etis_bicep_default minReplicas)"
bicep_max="$(etis_bicep_default maxReplicas)"

etis_header "ETIS Engineering Studio" "Production Configuration"

etis_section "Application"
etis_row "Environment" "PRODUCTION"
etis_row "Application" "${ETIS_AZURE_CONTAINER_APP}"
etis_row "Resource Group" "${ETIS_AZURE_RESOURCE_GROUP}"
etis_row "Region" "${location}"
etis_row "Public URL" "${ETIS_AZURE_PUBLIC_URL}"
etis_row "Azure FQDN" "${fqdn}"

printf '\n'
etis_section "Ingress"
etis_row "External Ingress" "$(etis_bool_word "${external}")"
etis_row "Target Port" "${target_port}"
etis_row "Revision Mode" "${revision_mode}"

printf '\n'
etis_section "Compute"
etis_row "CPU" "${cpu} vCPU"
etis_row "Memory" "${memory}"
etis_row "Runtime Min / Max" "${min_replicas} / ${max_replicas}"
etis_row "Bicep Min / Max" "${bicep_min} / ${bicep_max}"

printf '\n'
etis_section "Accepted Production Baseline"
etis_row "Minimum Replicas" "${ETIS_EXPECTED_MIN_REPLICAS}"
etis_row "Maximum Replicas" "${ETIS_EXPECTED_MAX_REPLICAS}"
etis_row "Revision Mode" "${ETIS_EXPECTED_REVISION_MODE}"

printf '\n'
printf 'Secret values are intentionally not displayed.\n'
