#!/usr/bin/env bash
# Shared helpers for the local pipeline.
#
# There is no CI server for this report, so ci/ imitates one: the same stage
# boundaries, the same pass/fail gate, the same artifact directory a runner
# would publish. Every stage script sources this file and is runnable on its
# own; ci/pipeline.sh just runs them in order.

set -euo pipefail

# --- paths ------------------------------------------------------------------
CI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$CI_DIR/.." && pwd)"
CATALOG_DIR="$ROOT_DIR/report"
ARTIFACTS_DIR="$ROOT_DIR/artifacts"
LOG_DIR="$CI_DIR/logs"
TEMPLATE_DOCX="$ROOT_DIR/templates/report-template.docx"

# Pin the toolchain: a report that builds today must build the same way later.
GRAMAX_CLI_VERSION="${GRAMAX_CLI_VERSION:-1.0.54}"

mkdir -p "$ARTIFACTS_DIR" "$LOG_DIR"

# --- output -----------------------------------------------------------------
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
  C_RESET=''; C_BOLD=''; C_DIM=''; C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''
fi

stage_begin() {
  STAGE_NAME="$1"
  STAGE_STARTED=$SECONDS
  printf '%s\n' "${C_BLUE}${C_BOLD}==> [$STAGE_NAME]${C_RESET} ${C_DIM}$(date +%H:%M:%S)${C_RESET}"
}

stage_end() {
  local elapsed=$(( SECONDS - STAGE_STARTED ))
  printf '%s\n\n' "${C_GREEN}    ok${C_RESET} ${C_DIM}[$STAGE_NAME] ${elapsed}s${C_RESET}"
}

info()  { printf '    %s\n' "$*"; }
warn()  { printf '%s\n' "${C_YELLOW}    warn${C_RESET} $*"; }
fail()  { printf '%s\n' "${C_RED}${C_BOLD}    FAIL${C_RESET} $*" >&2; exit 1; }

# --- gramax -----------------------------------------------------------------
# The CLI interleaves OpenTelemetry spans (`{"name":...}`) into its progress
# output, sometimes glued onto the end of a human-readable line. The raw stream
# goes to the stage log; the console gets the spans stripped off.
gramax() {
  local log="$LOG_DIR/${STAGE_NAME//:/-}.log" rc=0
  npx -y "gramax-cli@${GRAMAX_CLI_VERSION}" "$@" >"$log" 2>&1 || rc=$?
  # progress bars redraw with \r -- keep only what each line finally said
  sed -e 's/.*\r//' -e 's/{"name":.*$//' "$log" \
    | grep -v '^[[:space:]]*$' | sed 's/^/    /' || true
  return $rc
}
