#!/usr/bin/env bash
# Stage: export:pdf -- reading copy.
#
# Same source, second format: title page, table of contents and numbered
# headings come from flags, not from hand-formatting. Styling overrides go in
# templates/report-template.css.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "export:pdf"

out="$ARTIFACTS_DIR/report"
template_css="$ROOT_DIR/templates/report-template.css"
args=(export -s "$CATALOG_DIR" -o "$out" -y -f pdf --pdf-title --pdf-toc --pdf-number)

if [[ -f "$template_css" ]]; then
  args+=(-t "$template_css")
  info "template: ${template_css#"$ROOT_DIR"/}"
fi

gramax "${args[@]}" || fail "PDF export failed"

[[ -f "$out.pdf" ]] || fail "expected $out.pdf, not produced"
info "pdf: ${out#"$ROOT_DIR"/}.pdf  ($(du -h "$out.pdf" | cut -f1))"

stage_end
