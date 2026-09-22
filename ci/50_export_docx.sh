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

# Every embedded image must actually be the format its part name claims. An
# .svg referenced from an article is embedded as raw SVG bytes under a .png
# part name: the document builds, the pipeline is green, and the figure is
# blank when it is opened. Checking magic bytes is what catches it.
python3 - "$out.docx" <<'PY' || fail "DOCX contains malformed image parts"
import sys, zipfile

MAGIC = {
    "png":  [b"\x89PNG\r\n\x1a\n"],
    "jpg":  [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif":  [b"GIF87a", b"GIF89a"],
    "bmp":  [b"BM"],
    "emf":  [b"\x01\x00\x00\x00"],
    "wmf":  [b"\xd7\xcd\xc6\x9a", b"\x01\x00\x09\x00"],
}

bad = []
with zipfile.ZipFile(sys.argv[1]) as z:
    parts = [n for n in z.namelist() if n.startswith("word/media/") and not n.endswith("/")]
    for name in parts:
        ext = name.rsplit(".", 1)[-1].lower()
        head = z.read(name)[:16]
        expected = MAGIC.get(ext)
        if expected is None:
            print(f"    note: {name} -- unchecked extension .{ext}")
        elif not any(head.startswith(m) for m in expected):
            looks = "SVG" if head.lstrip()[:4] == b"<svg" else head[:8].hex()
            bad.append(f"{name} declares .{ext} but contains {looks}")

print(f"    embedded images: {len(parts)} checked, {len(bad)} malformed")
for b in bad:
    print(f"    malformed: {b}", file=sys.stderr)
sys.exit(1 if bad else 0)
PY

stage_end
