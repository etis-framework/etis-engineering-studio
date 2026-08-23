#!/usr/bin/env bash

# Shared presentation helpers for the ETIS Azure Operations CLI.
# Do not enable set -e here; this file is sourced by command scripts.

ETIS_OUTPUT_WIDTH="${ETIS_OUTPUT_WIDTH:-60}"

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  ETIS_COLOR_GREEN=$'\033[32m'
  ETIS_COLOR_YELLOW=$'\033[33m'
  ETIS_COLOR_RED=$'\033[31m'
  ETIS_COLOR_CYAN=$'\033[36m'
  ETIS_COLOR_BOLD=$'\033[1m'
  ETIS_COLOR_RESET=$'\033[0m'
else
  ETIS_COLOR_GREEN=''
  ETIS_COLOR_YELLOW=''
  ETIS_COLOR_RED=''
  ETIS_COLOR_CYAN=''
  ETIS_COLOR_BOLD=''
  ETIS_COLOR_RESET=''
fi

etis_rule() {
  printf '%*s\n' "${ETIS_OUTPUT_WIDTH}" '' | tr ' ' '='
}

etis_subrule() {
  printf '%*s\n' "${ETIS_OUTPUT_WIDTH}" '' | tr ' ' '-'
}

etis_header() {
  local title="${1:-ETIS Engineering Studio}"
  local subtitle="${2:-Azure Operations}"

  printf '\n'
  etis_rule
  printf ' %s\n' "${title}"
  printf ' %s\n' "${subtitle}"
  etis_rule
  printf '\n'
}

etis_section() {
  printf '%s%s%s\n' \
    "${ETIS_COLOR_BOLD}" \
    "${1}" \
    "${ETIS_COLOR_RESET}"
}

etis_row() {
  local label="$1"
  local value="${2:-}"
  local target_width=30
  local dot_count

  dot_count=$((target_width - ${#label}))
  if (( dot_count < 2 )); then
    dot_count=2
  fi

  printf '  %s ' "${label}"
  printf '%*s' "${dot_count}" '' | tr ' ' '.'
  printf ' %s\n' "${value}"
}

etis_status_value() {
  local state="$1"
  local detail="${2:-}"

  case "${state}" in
    PASS)
      printf '%sPASS%s%s' \
        "${ETIS_COLOR_GREEN}" \
        "${ETIS_COLOR_RESET}" \
        "${detail:+  ${detail}}"
      ;;
    WARN)
      printf '%sWARN%s%s' \
        "${ETIS_COLOR_YELLOW}" \
        "${ETIS_COLOR_RESET}" \
        "${detail:+  ${detail}}"
      ;;
    FAIL)
      printf '%sFAIL%s%s' \
        "${ETIS_COLOR_RED}" \
        "${ETIS_COLOR_RESET}" \
        "${detail:+  ${detail}}"
      ;;
    INFO)
      printf '%sINFO%s%s' \
        "${ETIS_COLOR_CYAN}" \
        "${ETIS_COLOR_RESET}" \
        "${detail:+  ${detail}}"
      ;;
    *)
      printf '%s' "${detail:-${state}}"
      ;;
  esac
}

etis_status_row() {
  local label="$1"
  local state="$2"
  local detail="${3:-}"
  local rendered

  rendered="$(etis_status_value "${state}" "${detail}")"
  etis_row "${label}" "${rendered}"
}

etis_note() {
  local heading="$1"
  shift

  printf '\n%s%s%s\n' \
    "${ETIS_COLOR_BOLD}" \
    "${heading}" \
    "${ETIS_COLOR_RESET}"

  while (( "$#" )); do
    printf '  %s\n' "$1"
    shift
  done
}

etis_final_status() {
  local label="$1"
  local state="$2"

  printf '\n'
  etis_subrule
  printf ' %s: ' "${label}"
  etis_status_value "${state}"
  printf '\n'
  etis_subrule
}

etis_die() {
  printf '%sERROR:%s %s\n' \
    "${ETIS_COLOR_RED}" \
    "${ETIS_COLOR_RESET}" \
    "$*" >&2
  exit 1
}
