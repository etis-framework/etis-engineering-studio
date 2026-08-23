#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_az_login
etis_require_container_app
etis_require_command python3

follow=false
raw=false
show_all=false
tail_count=50

while (( "$#" )); do
  case "$1" in
    --follow|-f)
      follow=true
      ;;
    --raw)
      raw=true
      ;;
    --all)
      show_all=true
      ;;
    --tail)
      shift
      [[ "${1:-}" =~ ^[0-9]+$ ]] \
        || etis_die "--tail requires a positive integer."
      tail_count="$1"
      ;;
    -h|--help)
      cat <<'USAGE'
Usage:
  ./scripts/azure/etis-azure logs
  ./scripts/azure/etis-azure logs --tail 100
  ./scripts/azure/etis-azure logs --all
  ./scripts/azure/etis-azure logs --raw
  ./scripts/azure/etis-azure logs --follow

Options:
  --tail N       Number of recent Azure log records (default: 50)
  --all          Include routine /health and /ready probe requests
  --raw          Show unformatted Azure log output
  --follow, -f   Stream live logs until Ctrl-C
USAGE
      exit 0
      ;;
    *)
      etis_die "Unknown logs option: $1"
      ;;
  esac
  shift
done

etis_header "ETIS Engineering Studio" "Production Logs"

etis_row "Application" "${ETIS_AZURE_CONTAINER_APP}"
etis_row "Resource Group" "${ETIS_AZURE_RESOURCE_GROUP}"

if [[ "${follow}" == true ]]; then
  printf '\n'
  etis_section "Live Log Stream"
  printf '  Live Azure output is shown without reformatting.\n'
  printf '  Ctrl-C to stop streaming.\n\n'

  exec az containerapp logs show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --type console \
    --follow \
    --tail "${tail_count}"
fi

log_output="$(
  az containerapp logs show \
    --name "${ETIS_AZURE_CONTAINER_APP}" \
    --resource-group "${ETIS_AZURE_RESOURCE_GROUP}" \
    --type console \
    --tail "${tail_count}"
)"

if [[ "${raw}" == true ]]; then
  printf '\n'
  etis_section "Raw Azure Console Logs"
  printf '  Showing up to %s records.\n\n' "${tail_count}"
  printf '%s\n' "${log_output}"
  exit 0
fi

printf '\n'
etis_section "Recent Activity"
printf '  Showing up to %s Azure log records.\n\n' "${tail_count}"

ETIS_LOG_OUTPUT="${log_output}" ETIS_LOG_SHOW_ALL="${show_all}" python3 - <<'PY'
import json
import os
from datetime import datetime

raw = os.environ.get("ETIS_LOG_OUTPUT", "")
show_all = os.environ.get("ETIS_LOG_SHOW_ALL", "false").lower() == "true"

records = []
http_requests = 0
http_errors = 0
application_errors = 0
health_probes = 0
readiness_probes = 0

for line in raw.splitlines():
    line = line.strip()
    if not line:
        continue

    try:
        outer = json.loads(line)
    except json.JSONDecodeError:
        records.append(("MESSAGE", "", "", "", "", line))
        continue

    timestamp = str(outer.get("TimeStamp") or "")
    message = str(outer.get("Log") or "")

    # Azure console output may prefix application JSON with a stream marker.
    candidate = message
    if len(candidate) >= 2 and candidate[1] == " ":
        candidate = candidate[2:]

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        records.append(("MESSAGE", timestamp, "", "", "", message))
        continue

    if isinstance(payload, dict) and payload.get("event") == "http_request":
        http_requests += 1

        method = str(payload.get("method") or "-")
        route = str(payload.get("route") or "-")
        status = payload.get("status_code")
        duration = payload.get("duration_ms")

        status_text = str(status) if status is not None else "-"
        duration_text = (
            f"{float(duration):.1f} ms"
            if isinstance(duration, (int, float))
            else "-"
        )

        if isinstance(status, int) and status >= 400:
            http_errors += 1

        if route == "/health":
            health_probes += 1
        elif route == "/ready":
            readiness_probes += 1

        if show_all or route not in {"/health", "/ready"} or (
            isinstance(status, int) and status >= 400
        ):
            records.append(
                (
                    "HTTP",
                    timestamp,
                    method,
                    route,
                    status_text,
                    duration_text,
                )
            )
    else:
        event = str(payload.get("event") or "application")
        level = str(payload.get("level") or payload.get("severity") or "")
        if level.lower() in {"error", "critical", "fatal"}:
            application_errors += 1

        records.append(
            (
                "EVENT",
                timestamp,
                event,
                "",
                "",
                json.dumps(payload, separators=(",", ":"))[:180],
            )
        )


def display_time(value):
    if not value:
        return "-"

    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%H:%M:%S")
    except ValueError:
        return value[:19]


http_rows = [record for record in records if record[0] == "HTTP"]
other_rows = [record for record in records if record[0] != "HTTP"]

if http_rows:
    print(
        f"  {'Time (UTC)':<12} "
        f"{'Method':<7} "
        f"{'Route':<22} "
        f"{'Status':<7} "
        f"{'Duration'}"
    )
    print(
        f"  {'----------':<12} "
        f"{'------':<7} "
        f"{'----------------------':<22} "
        f"{'------':<7} "
        f"{'--------'}"
    )

    for _, timestamp, method, route, status, duration in http_rows:
        print(
            f"  {display_time(timestamp):<12} "
            f"{method:<7} "
            f"{route[:22]:<22} "
            f"{status:<7} "
            f"{duration}"
        )
else:
    print("  No non-probe HTTP request records found.")

if other_rows:
    print()
    print("Other Messages")
    for kind, timestamp, field1, _, _, detail in other_rows:
        if kind == "MESSAGE":
            text = detail
        else:
            text = f"{field1}: {detail}"

        print(f"  {display_time(timestamp):<12} {text[:180]}")

print()
print("Summary")
print(f"  HTTP requests observed ....... {http_requests}")
print(f"  Health probes ................ {health_probes}")
print(f"  Readiness probes ............. {readiness_probes}")
print(f"  HTTP errors .................. {http_errors}")
print(f"  Application errors ........... {application_errors}")

if not show_all and (health_probes or readiness_probes):
    print()
    print("  Routine health/readiness probes are hidden.")
    print("  Use --all to include them.")
PY
