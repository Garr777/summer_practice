#!/usr/bin/env bash
# Stage: export:kfu -- fill the department's report form.
#
# The practice report is submitted on a КФУ form, which carries its own title
# page, contents and closing sections. Only two regions belong to us: the
# chapters and the bibliography. kfu/build_report.py writes those into a copy
# of the form and leaves the rest untouched.
#
# The form itself lives outside the repository (supplied by the user, excluded
# via .git/info/exclude), so the stage skips with a warning when it is absent
# rather than failing a clone that does not have it.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stage_begin "export:kfu"

form="$ROOT_DIR/Practice_docs/Отчет.docx"
if [[ ! -f "$form" ]]; then
  warn "form not found at Practice_docs/ -- skipping"
  stage_end
  exit 0
fi

out="$ARTIFACTS_DIR/Отчет.docx"
python3 "$ROOT_DIR/kfu/build_report.py" --out "$out" \
  || fail "filling the form failed"

# The form is not ours: verify we produced a valid document rather than assume.
python3 - "$out" <<'PY' || fail "assembled form failed validation"
import sys, zipfile, re
import xml.etree.ElementTree as ET
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
z = zipfile.ZipFile(sys.argv[1])
root = ET.fromstring(z.read("word/document.xml"))
text = "\n".join("".join(t.text or "" for t in p.iter(W + "t"))
                 for p in root.find(W + "body") if p.tag == W + "p")

problems = []
for keep in ("КАЗАНСКИЙ (ПРИВОЛЖСКИЙ) ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ", "Заключение",
             "Список использованных источников"):
    if keep not in text:
        problems.append(f"form section lost: {keep}")
for stub in ("Название главы зависит от задач", "Должны быть подробно описаны",
             "Number of smartphone users"):
    if stub in text:
        problems.append(f"template stub left in place: {stub}")
for n in (1, 2, 3, 4):
    if not re.search(rf"^{n}\. ", text, re.M):
        problems.append(f"chapter {n} missing")
for name, data in ((n, z.read(n)) for n in z.namelist() if n.startswith("word/media/")):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        problems.append(f"{name} is not a PNG")

print(f"    paragraphs: {len(text.splitlines())}, "
      f"tables: {len(list(root.iter(W + 'tbl')))}, "
      f"figures: {len(list(root.iter(W + 'drawing')))}")
for p in problems:
    print(f"    problem: {p}", file=sys.stderr)
sys.exit(1 if problems else 0)
PY

info "form: ${out#"$ROOT_DIR"/}  ($(du -h "$out" | cut -f1))"

stage_end
