#!/usr/bin/env bash
# Run every stage in order, the way a runner would.
#
#   ci/pipeline.sh            all stages
#   ci/pipeline.sh lint check just those, in the order given
#
# Stages are plain scripts named NN_<stage>.sh, so adding one is dropping a
# file in ci/ -- the same property that makes the GitLab mirror in
# .gitlab-ci.yml a thin wrapper rather than a second implementation.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

mapfile -t all_stages < <(find "$CI_DIR" -maxdepth 1 -name '[0-9][0-9]_*.sh' | sort)

if [[ $# -gt 0 ]]; then
  selected=()
  for want in "$@"; do
    match="$(printf '%s\n' "${all_stages[@]}" | grep -E "/[0-9]{2}_${want//:/_}\.sh$" || true)"
    [[ -n "$match" ]] || fail "no such stage: $want"
    selected+=("$match")
  done
else
  selected=("${all_stages[@]}")
fi

rm -rf "$LOG_DIR"; mkdir -p "$LOG_DIR"
started=$SECONDS
results=()

for stage in "${selected[@]}"; do
  name="$(basename "$stage" .sh | cut -d_ -f2-)"
  if bash "$stage"; then
    results+=("${C_GREEN}pass${C_RESET}  $name")
  else
    results+=("${C_RED}FAIL${C_RESET}  $name")
    printf '%s\n' "${C_BOLD}pipeline summary${C_RESET}"
    printf '  %s\n' "${results[@]}"
    printf '\n%s\n' "${C_RED}${C_BOLD}pipeline failed${C_RESET} after $(( SECONDS - started ))s"
    exit 1
  fi
done

printf '%s\n' "${C_BOLD}pipeline summary${C_RESET}"
printf '  %s\n' "${results[@]}"
printf '\n%s\n' "${C_GREEN}${C_BOLD}pipeline passed${C_RESET} in $(( SECONDS - started ))s"
printf '  artifacts: %s\n' "${ARTIFACTS_DIR#"$ROOT_DIR"/}/"
ls -1 "$ARTIFACTS_DIR" 2>/dev/null | sed 's/^/    /'
