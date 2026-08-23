#!/usr/bin/env bash

# Shared Azure/repository configuration and safety helpers.

ETIS_AZURE_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1
  pwd
)"

ETIS_REPO_ROOT="$(
  cd "${ETIS_AZURE_DIR}/../.." >/dev/null 2>&1
  pwd
)"

# Runtime defaults may be overridden intentionally by environment variables.
ETIS_AZURE_RESOURCE_GROUP="${ETIS_AZURE_RESOURCE_GROUP:-etis-studio-prod}"
ETIS_AZURE_CONTAINER_APP="${ETIS_AZURE_CONTAINER_APP:-etis-studio-prod}"
ETIS_AZURE_PUBLIC_URL="${ETIS_AZURE_PUBLIC_URL:-https://simulator.etisframework.org}"

# Accepted production baseline.
ETIS_EXPECTED_MIN_REPLICAS="${ETIS_EXPECTED_MIN_REPLICAS:-1}"
ETIS_EXPECTED_MAX_REPLICAS="${ETIS_EXPECTED_MAX_REPLICAS:-5}"
ETIS_EXPECTED_REVISION_MODE="${ETIS_EXPECTED_REVISION_MODE:-Single}"

etis_command_exists() {
  command -v "$1" >/dev/null 2>&1
}

etis_require_command() {
  etis_command_exists "$1" || etis_die "Required command not found: $1"
}

etis_require_repo() {
  [[ -f "${ETIS_REPO_ROOT}/infra/azure/app.bicep" ]] \
    || etis_die "Could not identify the ETIS Engineering Studio repository root."
}

etis_require_az_login() {
  etis_require_command az

  if ! az account show >/dev/null 2>&1; then
    etis_die "Azure CLI is not authenticated. Run 'az login' and try again."
  fi
}

etis_subscription_name() {
  az account show --query name -o tsv 2>/dev/null
}

etis_subscription_id() {
  az account show --query id -o tsv 2>/dev/null
}

etis_container_app_exists() {
  az containerapp show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --query name \
    -o tsv \
    >/dev/null 2>&1
}

etis_require_container_app() {
  etis_container_app_exists \
    || etis_die \
      "Azure Container App '${ETIS_AZURE_CONTAINER_APP}' was not found in resource group '${ETIS_AZURE_RESOURCE_GROUP}'."
}

etis_bicep_default() {
  local parameter="$1"

  awk -v parameter="${parameter}" '
    $1 == "param" && $2 == parameter {
      print $5
      exit
    }
  ' "${ETIS_REPO_ROOT}/infra/azure/app.bicep"
}

etis_bool_word() {
  case "${1:-}" in
    true|True|TRUE|1) printf 'Yes' ;;
    false|False|FALSE|0) printf 'No' ;;
    *) printf '%s' "${1:-Unknown}" ;;
  esac
}
