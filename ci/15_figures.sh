#!/usr/bin/env bash
# Stage: figures -- keep the shipped PNG in step with its SVG source.
#
# Diagrams are authored as SVG so they stay text: diffable, reviewable, edited
# without a binary tool. But an .svg referenced from an article is embedded by
# gramax into the DOCX as raw SVG bytes under a .png part name, which Word
# cannot render -- the figure silently arrives broken. So the article
# references the PNG, and this stage regenerates it from the SVG.
#
# The PNG is committed, so a fresh clone builds without a rasteriser. When one
# is unavailable the stage keeps the committed file, but refuses to let a PNG
# older than its SVG ship.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "figures"

shopt -s nullglob
svgs=("$CATALOG_DIR"/images/*.svg)
(( ${#svgs[@]} > 0 )) || { info "no SVG sources"; stage_end; exit 0; }

for svg in "${svgs[@]}"; do
  png="${svg%.svg}.png"
  rel="${svg#"$ROOT_DIR"/}"

  if python3 "$CI_DIR/render_svg.py" "$svg" "$png" 2>>"$LOG_DIR/figures.log"; then
    continue
  fi

  rc=$?
  [[ $rc -eq 3 ]] || fail "$rel: rasteriser failed (see ci/logs/figures.log)"

  # No rasteriser: the committed PNG has to exist and be current.
  [[ -f "$png" ]] || fail "$rel: no rasteriser and no committed ${png##*/}"
  [[ "$svg" -nt "$png" ]] \
    && fail "$rel is newer than ${png##*/} and no rasteriser is available -- install librsvg2-bin or python3-cairosvg"
  warn "no rasteriser; using committed ${png##*/}"
done

info "figures: ${#svgs[@]} SVG source(s)"

stage_end
