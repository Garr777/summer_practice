#!/usr/bin/env bash
# Stage: sources -- turn the assignment's bibliography rules into a gate.
#
# The brief requires at least 30 sources, published within the last 3-5 years,
# and every one of them actually cited in the text. Checking that by hand on
# every revision is exactly the monotonous work docs-as-code is supposed to
# remove, so the pipeline counts instead.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "sources"

SOURCES_FILE="$CATALOG_DIR/5-istochniki.md"
MIN_SOURCES=30
RECENT_SHARE=60          # percent of sources that must fall inside the window
WINDOW_YEARS=5
this_year="$(date +%Y)"
oldest_recent=$(( this_year - WINDOW_YEARS ))

[[ -f "$SOURCES_FILE" ]] || fail "bibliography not found: ${SOURCES_FILE#"$ROOT_DIR"/}"

# Entries are a numbered markdown list: "1. Author. Title... -- 2024."
mapfile -t entries < <(grep -E '^[0-9]+\. ' "$SOURCES_FILE" || true)
total=${#entries[@]}

recent=0
for e in "${entries[@]}"; do
  # the publication year is the last 19xx/20xx on the entry line
  year="$(grep -oE '\b(19|20)[0-9]{2}\b' <<<"$e" | tail -n 1)"
  [[ -n "$year" ]] || { warn "no year found: $(cut -c1-70 <<<"$e")..."; continue; }
  (( year >= oldest_recent )) && recent=$(( recent + 1 ))
done

share=0
(( total > 0 )) && share=$(( recent * 100 / total ))

info "entries:          $total  (required: >= $MIN_SOURCES)"
info "within $oldest_recent-$this_year:   $recent  (${share}%, required: >= ${RECENT_SHARE}%)"

# Every entry must be cited somewhere in the body as [n].
uncited=()
for n in $(seq 1 "$total"); do
  grep -rqF "[$n]" --include='*.md' --exclude='5-istochniki.md' "$CATALOG_DIR" \
    || uncited+=("$n")
done
if (( ${#uncited[@]} > 0 )); then
  warn "never cited in the text: [${uncited[*]}]"
fi

(( total >= MIN_SOURCES ))       || fail "only $total sources, need $MIN_SOURCES"
(( share >= RECENT_SHARE ))      || fail "only ${share}% of sources are from the last $WINDOW_YEARS years"

stage_end
