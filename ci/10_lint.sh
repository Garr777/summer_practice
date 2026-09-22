#!/usr/bin/env bash
# Stage: lint -- structural rules gramax-cli does not enforce.
#
# Catches the mistakes that only show up in the exported DOCX, when it is too
# late: an article with no front matter lands with a filename as its heading,
# two articles sharing an `order` come out in arbitrary sequence, and a TODO
# left behind gets printed and handed in.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "lint"

errors=0
report_error() { printf '%s\n' "${C_RED}    error${C_RESET} $*" >&2; errors=$(( errors + 1 )); }

mapfile -t articles < <(find "$CATALOG_DIR" -name '*.md' | sort)
[[ ${#articles[@]} -gt 0 ]] || fail "no articles found in $CATALOG_DIR"

for f in "${articles[@]}"; do
  rel="${f#"$ROOT_DIR"/}"

  # 1. front matter must open on line 1 -- gramax reads title/order from it
  [[ "$(head -n 1 "$f")" == "---" ]] \
    || report_error "$rel: missing front matter (file must start with ---)"

  front="$(awk 'NR>1 && /^---$/{exit} NR>1' "$f")"
  grep -q '^title:' <<<"$front" || report_error "$rel: front matter has no 'title:'"
  grep -q '^order:' <<<"$front" || report_error "$rel: front matter has no 'order:'"

  # 2. unfinished work must not reach an export
  if grep -nE 'TODO|FIXME|<!-- *draft *-->|ЗАГЛУШКА' "$f" >/dev/null; then
    while IFS= read -r hit; do report_error "$rel:$hit"; done \
      < <(grep -nE 'TODO|FIXME|<!-- *draft *-->|ЗАГЛУШКА' "$f" | cut -c1-100)
  fi

  # 3. tabs break markdown list nesting in the DOCX renderer
  grep -qP '^\t' "$f" && report_error "$rel: leading tab (use spaces)"
done

# 4. sibling articles must have distinct `order` -- otherwise section sequence
#    is undefined, and the printed report comes out shuffled
while IFS= read -r dir; do
  dupes="$(grep -h '^order:' "$dir"/*.md 2>/dev/null \
    | awk '{print $2}' | sort | uniq -d || true)"
  [[ -z "$dupes" ]] \
    || report_error "${dir#"$ROOT_DIR"/}: duplicate order value(s): $(tr '\n' ' ' <<<"$dupes")"
done < <(find "$CATALOG_DIR" -type d | sort)

info "articles checked: ${#articles[@]}"
[[ $errors -eq 0 ]] || fail "$errors structural error(s)"

stage_end
