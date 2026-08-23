#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/output.sh"
source "${SCRIPT_DIR}/lib/common.sh"

etis_require_az_login
etis_require_command python3

ETIS_BUDGET_NAME="${ETIS_BUDGET_NAME:-etis-studio-prod-monthly}"
ETIS_EXPECTED_MONTHLY_BUDGET="${ETIS_EXPECTED_MONTHLY_BUDGET:-100}"

error_file="$(mktemp "${TMPDIR:-/tmp}/etis-budget-error-XXXXXX")"

cleanup() {
  rm -f "${error_file}"
}
trap cleanup EXIT

if ! budget_json="$(
  az consumption budget list \
    --query "[?name=='${ETIS_BUDGET_NAME}'] | [0]" \
    -o json \
    2>"${error_file}"
)"; then
  etis_header "ETIS Engineering Studio" "Azure Budget"

  etis_section "Budget"
  etis_status_row "Budget Query" "FAIL" "Azure budget query failed"

  if [[ -s "${error_file}" ]]; then
    etis_note \
      "Azure Response" \
      "$(tr '\n' ' ' < "${error_file}" | cut -c1-240)"
  fi

  etis_final_status "BUDGET" "FAIL"
  exit 1
fi

if [[ -z "${budget_json}" || "${budget_json}" == "null" ]]; then
  etis_header "ETIS Engineering Studio" "Azure Budget"

  etis_section "Budget"
  etis_status_row \
    "Production Budget" \
    "FAIL" \
    "budget '${ETIS_BUDGET_NAME}' was not found"

  etis_final_status "BUDGET" "FAIL"
  exit 1
fi

ETIS_BUDGET_JSON="${budget_json}" \
ETIS_EXPECTED_BUDGET="${ETIS_EXPECTED_MONTHLY_BUDGET}" \
python3 - <<'PY' > "${error_file}.parsed"
import json
import os
from decimal import Decimal, InvalidOperation

payload = json.loads(os.environ["ETIS_BUDGET_JSON"])
expected = Decimal(os.environ["ETIS_EXPECTED_BUDGET"])

amount_raw = payload.get("amount")
try:
    amount = Decimal(str(amount_raw))
except (InvalidOperation, TypeError):
    amount = None

name = str(payload.get("name") or "-")
grain = str(payload.get("timeGrain") or "-")

period = payload.get("timePeriod") or {}
start = str(period.get("startDate") or "-")
end = str(period.get("endDate") or "-")

notifications = payload.get("notifications") or {}

print(f"name={name}")
print(f"amount={amount if amount is not None else ''}")
print(f"grain={grain}")
print(f"start={start}")
print(f"end={end}")
print(f"amount_status={'PASS' if amount == expected else 'FAIL'}")

entries = []

for notification_name, notification in notifications.items():
    if not isinstance(notification, dict):
        continue

    enabled = bool(notification.get("enabled"))
    threshold = notification.get("threshold")
    operator = str(notification.get("operator") or "-")

    emails = notification.get("contactEmails") or []
    groups = notification.get("contactGroups") or []
    roles = notification.get("contactRoles") or []

    recipients = len(emails) + len(groups) + len(roles)

    try:
        threshold_number = Decimal(str(threshold))
    except (InvalidOperation, TypeError):
        continue

    entries.append(
        (
            threshold_number,
            enabled,
            operator,
            recipients,
            notification_name,
        )
    )

entries.sort(key=lambda item: item[0])

for threshold, enabled, operator, recipients, name in entries:
    print(
        "alert="
        f"{threshold}|"
        f"{'true' if enabled else 'false'}|"
        f"{operator}|"
        f"{recipients}|"
        f"{name}"
    )
PY

parsed_file="${error_file}.parsed"
trap 'rm -f "${error_file}" "${parsed_file}"' EXIT

name="$(grep '^name=' "${parsed_file}" | cut -d= -f2-)"
amount="$(grep '^amount=' "${parsed_file}" | cut -d= -f2-)"
grain="$(grep '^grain=' "${parsed_file}" | cut -d= -f2-)"
start="$(grep '^start=' "${parsed_file}" | cut -d= -f2-)"
end="$(grep '^end=' "${parsed_file}" | cut -d= -f2-)"
amount_status="$(grep '^amount_status=' "${parsed_file}" | cut -d= -f2-)"

start_date="${start%%T*}"
end_date="${end%%T*}"

overall="PASS"

etis_header "ETIS Engineering Studio" "Azure Budget"

etis_section "Production Budget"
etis_row "Budget Name" "${name}"
etis_row "Time Grain" "${grain}"
etis_row "Budget Period" "${start_date} through ${end_date}"

if [[ "${amount_status}" == "PASS" ]]; then
  etis_status_row "Monthly Budget" "PASS" "\$${amount}"
else
  etis_status_row \
    "Monthly Budget" \
    "FAIL" \
    "expected \$${ETIS_EXPECTED_MONTHLY_BUDGET}, actual \$${amount:-unknown}"
  overall="FAIL"
fi

printf '\n'
etis_section "Alert Thresholds"

alert_count=0

while IFS= read -r line; do
  [[ "${line}" == alert=* ]] || continue

  alert_count=$((alert_count + 1))
  payload="${line#alert=}"

  IFS='|' read -r threshold enabled operator recipients notification_name <<<"${payload}"

  if [[ "${enabled}" == "true" && "${recipients}" =~ ^[0-9]+$ && "${recipients}" -gt 0 ]]; then
    etis_status_row \
      "${threshold}% Actual Cost" \
      "PASS" \
      "enabled, ${recipients} recipient(s)"
  else
    etis_status_row \
      "${threshold}% Actual Cost" \
      "FAIL" \
      "enabled=${enabled}, recipients=${recipients}"
    overall="FAIL"
  fi
done < "${parsed_file}"

if (( alert_count == 0 )); then
  etis_status_row "Budget Alerts" "FAIL" "no notifications configured"
  overall="FAIL"
fi

printf '\n'
etis_note \
  "Operational Meaning" \
  "Budget alerts provide spend visibility; they do not stop Azure resources." \
  "Production health and billing controls are evaluated separately."

etis_final_status "BUDGET" "${overall}"

[[ "${overall}" != "FAIL" ]]
