#!/usr/bin/env bash
# Stage: check -- gramax's own catalog validation.
#
# Resolves internal links, image and diagram references, and flags elements the
# DOCX/PDF renderers cannot represent. Runs before any export so a broken link
# fails the pipeline instead of silently vanishing from the handed-in document.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "check"

gramax check -d "$CATALOG_DIR" -o "$LOG_DIR/gramax-check.txt" \
  || fail "catalog validation failed (see $LOG_DIR/gramax-check.txt)"

stage_end
