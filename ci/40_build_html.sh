#!/usr/bin/env bash
# Stage: build:html -- the browsable version of the report.
#
# A static site is the artifact a reviewer opens; the DOCX is what gets handed
# in. Building it here also front-runs the PDF export, which renders the same
# site internally, so a failure surfaces at a stage whose name explains it.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "build:html"

out="$ARTIFACTS_DIR/site"
rm -rf "$out"

gramax build -s "$CATALOG_DIR" -d "$out" --skip-check \
  || fail "static site build failed"

[[ -f "$out/index.html" ]] || fail "build produced no index.html"
info "site: ${out#"$ROOT_DIR"/}  ($(du -sh "$out" | cut -f1))"

stage_end
