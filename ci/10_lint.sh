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

  # 4. gramax renders the front-matter title as the article's heading, so a
  #    body H1 repeating it prints the section title twice in the export --
  #    invisible in Markdown, obvious only in the handed-in document
  title="$(sed -n 's/^title: *//p' <<<"$front" | head -n 1 | tr -d '"'"'"'')"
  body_h1="$(awk 'NR>1 && /^---$/{f=1; next} f && NF {print; exit}' "$f")"
  [[ -n "$title" && "$body_h1" == "# $title" ]] \
    && report_error "$rel: body H1 repeats the front-matter title"
done

# 4. items at one level must have distinct `order` -- otherwise the sequence is
#    undefined and the printed report comes out shuffled. A level's items are
#    the plain articles in the directory plus each subdirectory, which is
#    represented by its own _index.md: a section's order belongs to the level
#    above it, not beside its own children.
while IFS= read -r dir; do
  orders=()
  for f in "$dir"/*.md; do
    [[ -e "$f" && "$(basename "$f")" != "_index.md" ]] || continue
    orders+=("$(awk -F': *' '/^order:/{print $2; exit}' "$f")")
  done
  for sub in "$dir"/*/; do
    [[ -f "$sub/_index.md" ]] || continue
    orders+=("$(awk -F': *' '/^order:/{print $2; exit}' "$sub/_index.md")")
  done
  (( ${#orders[@]} > 0 )) || continue
  dupes="$(printf '%s\n' "${orders[@]}" | sort | uniq -d)"
  [[ -z "$dupes" ]] \
    || report_error "${dir#"$ROOT_DIR"/}: duplicate order value(s): $(tr '\n' ' ' <<<"$dupes")"
done < <(find "$CATALOG_DIR" -type d | sort)

# 5. {{PLACEHOLDER}} tokens are reported but do not fail the build: the title
#    page is filled in from the department's form, and the pipeline has to stay
#    runnable before that happens.
mapfile -t placeholders < <(grep -rhoE '\{\{[A-ZА-Я_]+\}\}' "$CATALOG_DIR" | sort -u)
if (( ${#placeholders[@]} > 0 )); then
  warn "unfilled placeholders: ${placeholders[*]}"
fi

info "articles checked: ${#articles[@]}"
[[ $errors -eq 0 ]] || fail "$errors structural error(s)"

stage_end
