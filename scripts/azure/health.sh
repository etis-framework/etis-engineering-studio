#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_command curl

etis_header "ETIS Engineering Studio" "Production Health"

overall="PASS"

check_endpoint() {
  local label="$1"
  local path="$2"
  local expected_status="$3"
  local url="${ETIS_AZURE_PUBLIC_URL}${path}"
  local tmp
  local result
  local http_code
  local time_total

  tmp="$(mktemp)"
  trap 'rm -f "${tmp}"' RETURN

  result="$(
    curl \
      --silent \
      --show-error \
      --output "${tmp}" \
      --write-out '%{http_code}\t%{time_total}' \
      --max-time 15 \
      "${url}" \
      2>/dev/null || true
  )"

  IFS=$'\t' read -r http_code time_total <<<"${result}"

  http_code="${http_code:-000}"
  time_total="${time_total:-0}"

  if [[ "${http_code}" == "${expected_status}" ]]; then
    etis_status_row "${label}" "PASS" "HTTP ${http_code}"
  else
    etis_status_row \
      "${label}" \
      "FAIL" \
      "expected HTTP ${expected_status}, actual ${http_code}"
    overall="FAIL"
  fi

  response_ms="$(
    python3 - <<PY
value = float("${time_total:-0}")
print(f"{value * 1000:.0f} ms")
PY
  )"

  etis_row "${label} Response Time" "${response_ms}"

  if [[ -s "${tmp}" ]]; then
    payload="$(
      python3 - "${tmp}" <<'PY'
import json
import sys

path = sys.argv[1]
raw = open(path, "r", encoding="utf-8", errors="replace").read().strip()

try:
    data = json.loads(raw)
except Exception:
    print(raw[:160].replace("\n", " "))
else:
    if isinstance(data, dict):
        interesting = []
        for key in ("status", "migration_current", "environment"):
            if key in data:
                interesting.append(f"{key}={data[key]}")
        print(", ".join(interesting) if interesting else json.dumps(data, separators=(",", ":"))[:160])
    else:
        print(str(data)[:160])
PY
    )"

    [[ -n "${payload}" ]] && etis_row "${label} Payload" "${payload}"
  fi

  rm -f "${tmp}"
  trap - RETURN
}

etis_section "Public Endpoints"

check_endpoint "Health" "/health" "200"

printf '\n'
check_endpoint "Readiness" "/ready" "200"

printf '\n'
etis_section "Authentication Boundary"

auth_tmp="$(mktemp)"
trap 'rm -f "${auth_tmp}"' EXIT

auth_result="$(
  curl \
    --silent \
    --show-error \
    --output "${auth_tmp}" \
    --write-out '%{http_code}\t%{redirect_url}' \
    --max-time 15 \
    "${ETIS_AZURE_PUBLIC_URL}/" \
    2>/dev/null || true
)"

IFS=$'\t' read -r auth_code redirect_url <<<"${auth_result}"
auth_code="${auth_code:-000}"

case "${auth_code}" in
  200|302|303|307|308)
    etis_status_row "Unauthenticated Entry" "PASS" "HTTP ${auth_code}"
    ;;
  *)
    etis_status_row "Unauthenticated Entry" "FAIL" "HTTP ${auth_code}"
    overall="FAIL"
    ;;
esac

if [[ -n "${redirect_url:-}" ]]; then
  etis_row "Redirect Target" "${redirect_url}"
fi

etis_final_status "HEALTH" "${overall}"

[[ "${overall}" != "FAIL" ]]
