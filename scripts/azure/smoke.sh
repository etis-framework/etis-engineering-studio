#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/output.sh"
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_command curl
etis_require_command python3

overall="PASS"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/etis-smoke-XXXXXX")"

cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

etis_header "ETIS Engineering Studio" "Production Smoke Test"

request() {
  local url="$1"
  local body_file="$2"
  local headers_file="$3"

  curl \
    --silent \
    --show-error \
    --dump-header "${headers_file}" \
    --output "${body_file}" \
    --write-out '%{http_code}\t%{time_total}\t%{redirect_url}' \
    --max-time 20 \
    "${url}" \
    2>/dev/null || true
}

to_ms() {
  python3 -c '
import sys
try:
    print(f"{float(sys.argv[1]) * 1000:.0f}")
except Exception:
    print("0")
' "$1"
}

check_latency() {
  local label="$1"
  local milliseconds="$2"

  if [[ ! "${milliseconds}" =~ ^[0-9]+$ ]]; then
    etis_status_row "${label}" "WARN" "unable to measure"
    [[ "${overall}" == "PASS" ]] && overall="WARN"
  elif (( milliseconds <= 2000 )); then
    etis_status_row "${label}" "PASS" "${milliseconds} ms"
  elif (( milliseconds <= 5000 )); then
    etis_status_row "${label}" "WARN" "${milliseconds} ms"
    [[ "${overall}" == "PASS" ]] && overall="WARN"
  else
    etis_status_row "${label}" "WARN" "${milliseconds} ms — investigate latency"
    [[ "${overall}" == "PASS" ]] && overall="WARN"
  fi
}

printf '\n'
etis_section "Application Endpoints"

health_body="${tmp_dir}/health.body"
health_headers="${tmp_dir}/health.headers"
health_result="$(request "${ETIS_AZURE_PUBLIC_URL}/health" "${health_body}" "${health_headers}")"

IFS=$'\t' read -r health_code health_time health_redirect <<<"${health_result}"
health_code="${health_code:-000}"
health_ms="$(to_ms "${health_time:-0}")"

if [[ "${health_code}" == "200" ]]; then
  etis_status_row "Health Endpoint" "PASS" "HTTP 200"
else
  etis_status_row "Health Endpoint" "FAIL" "HTTP ${health_code}"
  overall="FAIL"
fi

check_latency "Health Response Time" "${health_ms}"

health_validation="$(
  python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    if data.get("status") == "ok" and data.get("environment") == "production":
        print("ok")
    else:
        print("status=%s,environment=%s" % (
            data.get("status"),
            data.get("environment"),
        ))
except Exception:
    print("invalid")
' "${health_body}"
)"

if [[ "${health_validation}" == "ok" ]]; then
  etis_status_row "Health Payload" "PASS" "production / ok"
else
  etis_status_row "Health Payload" "FAIL" "${health_validation}"
  overall="FAIL"
fi

ready_body="${tmp_dir}/ready.body"
ready_headers="${tmp_dir}/ready.headers"
ready_result="$(request "${ETIS_AZURE_PUBLIC_URL}/ready" "${ready_body}" "${ready_headers}")"

IFS=$'\t' read -r ready_code ready_time ready_redirect <<<"${ready_result}"
ready_code="${ready_code:-000}"
ready_ms="$(to_ms "${ready_time:-0}")"

if [[ "${ready_code}" == "200" ]]; then
  etis_status_row "Readiness Endpoint" "PASS" "HTTP 200"
else
  etis_status_row "Readiness Endpoint" "FAIL" "HTTP ${ready_code}"
  overall="FAIL"
fi

check_latency "Readiness Response Time" "${ready_ms}"

ready_validation="$(
  python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    if data.get("status") == "ready" and data.get("migration_current") is True:
        print("ok")
    else:
        print("status=%s,migration_current=%s" % (
            data.get("status"),
            data.get("migration_current"),
        ))
except Exception:
    print("invalid")
' "${ready_body}"
)"

if [[ "${ready_validation}" == "ok" ]]; then
  etis_status_row "Readiness Payload" "PASS" "ready / migrations current"
else
  etis_status_row "Readiness Payload" "FAIL" "${ready_validation}"
  overall="FAIL"
fi

printf '\n'
etis_section "Unauthenticated Entry"

root_body="${tmp_dir}/root.body"
root_headers="${tmp_dir}/root.headers"
root_result="$(request "${ETIS_AZURE_PUBLIC_URL}/" "${root_body}" "${root_headers}")"

IFS=$'\t' read -r root_code root_time root_redirect <<<"${root_result}"
root_code="${root_code:-000}"
root_ms="$(to_ms "${root_time:-0}")"

if [[ "${root_code}" == "200" ]]; then
  etis_status_row "Root Page" "PASS" "HTTP 200"
else
  etis_status_row "Root Page" "FAIL" "HTTP ${root_code}"
  overall="FAIL"
fi

check_latency "Root Response Time" "${root_ms}"

if grep -Fq 'id="loginGate"' "${root_body}" \
  && grep -Fq 'Sign in with Loyola' "${root_body}" \
  && grep -Fq 'href="/auth/entra"' "${root_body}"; then
  etis_status_row "Loyola Sign-In Gate" "PASS" "present"
else
  etis_status_row "Loyola Sign-In Gate" "FAIL" "expected login markup missing"
  overall="FAIL"
fi

if grep -Fq '<div id="appShell" class="shell hidden" hidden>' "${root_body}"; then
  etis_status_row \
    "Application Shell" \
    "PASS" \
    "native fail-closed protection present"
else
  etis_status_row \
    "Application Shell" \
    "FAIL" \
    "native hidden protection missing"
  overall="FAIL"
fi

printf '\n'
etis_section "Authentication Entry Point"

auth_body="${tmp_dir}/auth.body"
auth_headers="${tmp_dir}/auth.headers"
auth_result="$(request "${ETIS_AZURE_PUBLIC_URL}/auth/entra" "${auth_body}" "${auth_headers}")"

IFS=$'\t' read -r auth_code auth_time auth_redirect <<<"${auth_result}"
auth_code="${auth_code:-000}"
auth_ms="$(to_ms "${auth_time:-0}")"

case "${auth_code}" in
  302|303|307|308)
    etis_status_row "Loyola SSO Entry" "PASS" "HTTP ${auth_code}"
    ;;
  *)
    etis_status_row "Loyola SSO Entry" "FAIL" "HTTP ${auth_code}"
    overall="FAIL"
    ;;
esac

check_latency "SSO Entry Response Time" "${auth_ms}"

location_header="$(
  awk '
    BEGIN { IGNORECASE=1 }
    /^location:/ {
      sub(/\r$/, "")
      sub(/^[^:]+:[[:space:]]*/, "")
      print
      exit
    }
  ' "${auth_headers}"
)"

if [[ "${auth_redirect:-}" == https://login.microsoftonline.com/* ]] \
  || [[ "${location_header}" == https://login.microsoftonline.com/* ]]; then
  etis_status_row \
    "SSO Redirect Target" \
    "PASS" \
    "Microsoft identity platform"
else
  etis_status_row \
    "SSO Redirect Target" \
    "FAIL" \
    "unexpected or missing redirect"
  overall="FAIL"
fi

if [[ "${overall}" == "FAIL" ]]; then
  etis_note \
    "Next Action" \
    "Run ./scripts/azure/etis-azure status and health." \
    "Use ./scripts/azure/etis-azure logs if the endpoint checks do not explain the failure."
elif [[ "${overall}" == "WARN" ]]; then
  etis_note \
    "Next Action" \
    "Production is reachable, but one or more response-time checks deserve attention." \
    "Compare with ./scripts/azure/etis-azure logs and replicas."
fi

etis_final_status "SMOKE TEST" "${overall}"

[[ "${overall}" != "FAIL" ]]
