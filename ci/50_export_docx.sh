#!/usr/bin/env bash
# Stage: export:docx -- the deliverable.
#
# What actually gets handed in. Rendered through a corporate/GOST .docx
# template when one is present in templates/, so the styling lives in a
# versioned file rather than in someone's Word session.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "export:docx"

out="$ARTIFACTS_DIR/report"
args=(export -s "$CATALOG_DIR" -o "$out" -y -f docx)

if [[ -f "$TEMPLATE_DOCX" ]]; then
  args+=(-t "$TEMPLATE_DOCX")
  info "template: ${TEMPLATE_DOCX#"$ROOT_DIR"/}"
else
  warn "no template at ${TEMPLATE_DOCX#"$ROOT_DIR"/} -- exporting with gramax defaults"
fi

gramax "${args[@]}" || fail "DOCX export failed"

[[ -f "$out.docx" ]] || fail "expected $out.docx, not produced"
info "docx: ${out#"$ROOT_DIR"/}.docx  ($(du -h "$out.docx" | cut -f1))"

stage_end
