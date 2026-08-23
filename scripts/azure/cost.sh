#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/output.sh"
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_az_login
etis_require_command python3

subscription_id="$(etis_subscription_id)"
subscription_name="$(etis_subscription_name)"

from_date="$(
  python3 -c '
from datetime import date
today = date.today()
print(today.replace(day=1).isoformat())
'
)"

through_date="$(
  python3 -c '
from datetime import date
print(date.today().isoformat())
'
)"

request_body="$(
  python3 - "${from_date}" "${through_date}" <<'PY'
import json
import sys

start = sys.argv[1]
end = sys.argv[2]

print(json.dumps({
    "type": "ActualCost",
    "timeframe": "Custom",
    "timePeriod": {
        "from": f"{start}T00:00:00Z",
        "to": f"{end}T23:59:59Z",
    },
    "dataset": {
        "granularity": "None",
        "aggregation": {
            "totalCost": {
                "name": "Cost",
                "function": "Sum",
            }
        },
        "grouping": [
            {
                "type": "Dimension",
                "name": "ResourceGroupName",
            }
        ],
    },
}))
PY
)"

cost_url="https://management.azure.com/subscriptions/${subscription_id}/providers/Microsoft.CostManagement/query?api-version=2023-03-01"

response_file="$(mktemp "${TMPDIR:-/tmp}/etis-cost-response-XXXXXX")"
error_file="$(mktemp "${TMPDIR:-/tmp}/etis-cost-error-XXXXXX")"

cleanup() {
  rm -f "${response_file}" "${error_file}"
}
trap cleanup EXIT

attempt=1
max_attempts=3
success=false
throttled=false

while (( attempt <= max_attempts )); do
  : > "${response_file}"
  : > "${error_file}"

  if az rest \
      --method post \
      --url "${cost_url}" \
      --body "${request_body}" \
      --output json \
      >"${response_file}" \
      2>"${error_file}"; then
    success=true
    break
  fi

  if grep -Eqi '429|Too Many Requests' "${error_file}"; then
    throttled=true

    if (( attempt < max_attempts )); then
      if (( attempt == 1 )); then
        sleep 2
      else
        sleep 5
      fi
    fi
  else
    break
  fi

  attempt=$((attempt + 1))
done

etis_header "ETIS Engineering Studio" "Azure Cost"

etis_section "Query"
etis_row "Subscription" "${subscription_name}"
etis_row "Period" "${from_date} through ${through_date}"

if [[ "${success}" != true ]]; then
  printf '\n'
  etis_section "Cost Management"

  if [[ "${throttled}" == true ]]; then
    etis_status_row \
      "Billing Telemetry" \
      "WARN" \
      "Azure Cost Management is throttling requests"

    etis_note \
      "Impact" \
      "Studio production health is unaffected." \
      "Current cost data is temporarily unavailable from Azure."

    etis_note \
      "Next Action" \
      "No immediate action is required." \
      "Run this command again later; repeated manual retries are not recommended."

    etis_final_status "COST" "WARN"
    exit 0
  fi

  etis_status_row \
    "Billing Telemetry" \
    "FAIL" \
    "Azure Cost Management query failed"

  if [[ -s "${error_file}" ]]; then
    etis_note \
      "Azure Response" \
      "$(tr '\n' ' ' < "${error_file}" | cut -c1-240)"
  fi

  etis_final_status "COST" "FAIL"
  exit 1
fi

printf '\n'
etis_section "Month-to-Date Cost"

ETIS_COST_RESPONSE_FILE="${response_file}" python3 - <<'PY'
import json
import os
from decimal import Decimal, InvalidOperation

with open(
    os.environ["ETIS_COST_RESPONSE_FILE"],
    "r",
    encoding="utf-8",
) as handle:
    payload = json.load(handle)

properties = payload.get("properties") or {}
columns = properties.get("columns") or []
rows = properties.get("rows") or []

names = [str(c.get("name") or "") for c in columns]
indexes = {name.lower(): i for i, name in enumerate(names)}

cost_index = indexes.get("cost")
if cost_index is None:
    cost_index = indexes.get("pretaxcost")

group_index = indexes.get("resourcegroupname")
currency_index = indexes.get("currency")

if cost_index is None:
    raise SystemExit(
        "Cost Management response did not include a cost column."
    )

records = []
etis_total = Decimal("0")
subscription_total = Decimal("0")
currency = "USD"

for row in rows:
    try:
        value = Decimal(str(row[cost_index]))
    except (InvalidOperation, IndexError):
        continue

    subscription_total += value

    group = "(no resource group)"
    if group_index is not None and group_index < len(row):
        group = str(row[group_index] or group)

    if currency_index is not None and currency_index < len(row):
        currency = str(row[currency_index] or currency)

    normalized = group.lower()
    is_etis = (
        "etis-studio-prod" in normalized
        or normalized.startswith("me_etis-studio-prod")
    )

    if is_etis:
        etis_total += value

    records.append((group, value, is_etis))

records.sort(key=lambda item: item[1], reverse=True)

if records:
    print(f"  {'Resource Group':<52} {'Cost':>10}")
    print(
        f"  {'----------------------------------------------------':<52} "
        f"{'----------':>10}"
    )

    for group, value, is_etis in records:
        marker = "*" if is_etis else " "
        print(
            f"{marker} {group[:50]:<52} "
            f"{currency} {value:>7.2f}"
        )

    print()
    print(
        "  * ETIS Engineering Studio production-related "
        "resource group"
    )
else:
    print("  No month-to-date cost rows were returned.")

print()
print(
    f"  {'Observed ETIS total':<30} "
    f"{currency} {etis_total:.2f}"
)
print(
    f"  {'Subscription total':<30} "
    f"{currency} {subscription_total:.2f}"
)
PY

printf '\n'
etis_note \
  "Reporting Note" \
  "Azure Cost Management data can lag behind current resource usage." \
  "This command is informational and is not a production-health check."

etis_final_status "COST" "PASS"
