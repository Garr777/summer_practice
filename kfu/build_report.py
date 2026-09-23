#!/usr/bin/env python3
"""
Собрать тело отчёта КФУ: kfu/body/*.md -> Practice_docs/Отчет.docx.

Заполняются две области формы, остальное не трогается:
  * главы      -- между «… (Название главы зависит от задач)» и «Заключение»;
  * источники  -- после заголовка «Список использованных источников».

Форматирование задаётся прямым (direct) форматированием каждого абзаца, а не
стилями: в самой форме шрифт по умолчанию Georgia, тогда как требования кафедры
предписывают Times New Roman 14 пт с интервалом 1,5. Прямое форматирование
делает результат независимым от стилей формы.

Ссылки на источники в исходных файлах проставлены номерами полного перечня
(report/5-istochniki.md). Сборщик перенумеровывает их по первому упоминанию и
оставляет в списке только процитированные.

    python3 kfu/build_report.py [--out путь.docx]
"""
import argparse
import pathlib
import re
import shutil
import struct
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
BODY = ROOT / "kfu" / "body"
FORM = ROOT / "Practice_docs" / "Отчет.docx"
MASTER_SOURCES = ROOT / "report" / "5-istochniki.md"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# --- параметры оформления (требования кафедры) ---
FONT = "Times New Roman"
SZ = 28            # 14 пт в полуточках
CODE_FONT = "Courier New"
CODE_SZ = 22       # 11 пт
LINE = 360         # интервал 1,5 (240 = одинарный)
INDENT = 709       # абзацный отступ 1,25 см в твипах
TEXT_WIDTH_EMU = 165 * 36000   # ширина полосы набора: 210 - 30 - 15 мм


# ────────────────────────────── разметка ──────────────────────────────

def runs(text, sz=None):
    """Инлайн-разметка -> последовательность <w:r>."""
    sz = sz or SZ
    out = []
    token = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\*[^*]+?\*)')
    for part in token.split(text):
        if not part:
            continue
        bold = italic = code = False
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            part, bold = part[2:-2], True
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            part, code = part[1:-1], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, italic = part[1:-1], True
        part = part.replace("$", "")          # формулы отдаются как обычный текст
        rpr = [f'<w:rFonts w:ascii="{CODE_FONT if code else FONT}" '
               f'w:hAnsi="{CODE_FONT if code else FONT}" '
               f'w:cs="{CODE_FONT if code else FONT}"/>',
               f'<w:sz w:val="{CODE_SZ if code else sz}"/>',
               f'<w:szCs w:val="{CODE_SZ if code else sz}"/>']
        if bold:
            rpr.append("<w:b/>")
        if italic:
            rpr.append("<w:i/>")
        out.append(f'<w:r><w:rPr>{"".join(rpr)}</w:rPr>'
                   f'<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return "".join(out)


def para(text, *, align="both", indent=True, bold=False, before=0, after=0,
         page_break=False, keep_next=False):
    ppr = [f'<w:spacing w:line="{LINE}" w:lineRule="auto" '
           f'w:before="{before}" w:after="{after}"/>',
           f'<w:jc w:val="{align}"/>']
    if indent:
        ppr.append(f'<w:ind w:firstLine="{INDENT}"/>')
    if keep_next:
        ppr.append("<w:keepNext/>")
    body = runs(f"**{text}**" if bold else text) if text else ""
    brk = ('<w:r><w:br w:type="page"/></w:r>') if page_break else ""
    return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{brk}{body}</w:p>'


def table(rows):
    # широкая таблица при 14 пт дробит содержимое на обрывки строк; 12 пт читается
    sz = 24 if max(len(r) for r in rows) >= 5 else SZ
    widths = _column_widths(rows)
    total = sum(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [f'<w:tbl><w:tblPr>'
           f'<w:tblW w:w="{total}" w:type="dxa"/>'
           f'<w:tblBorders>' +
           "".join(f'<w:{e} w:val="single" w:sz="4" w:color="000000"/>'
                   for e in ("top", "left", "bottom", "right", "insideH", "insideV")) +
           f'</w:tblBorders>'
           f'<w:tblLayout w:type="fixed"/>'
           f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, row in enumerate(rows):
        cells = []
        for j, cell in enumerate(row):
            w = widths[j] if j < len(widths) else widths[-1]
            p = (f'<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto" '
                 f'w:before="20" w:after="20"/><w:jc w:val="left"/></w:pPr>'
                 f'{runs(f"**{cell}**" if i == 0 else cell, sz=sz)}</w:p>')
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
                         f'<w:vAlign w:val="center"/></w:tcPr>{p}</w:tc>')
        header = '<w:trPr><w:tblHeader/></w:trPr>' if i == 0 else ""
        out.append(f"<w:tr>{header}{''.join(cells)}</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def _column_widths(rows, total=9354):
    """Доли по длине содержимого; 9354 твипа = 165 мм полосы набора."""
    n = max(len(r) for r in rows)
    weight = [0] * n
    for r in rows:
        for j, c in enumerate(r[:n]):
            weight[j] = max(weight[j], min(len(c), 90))
    s = sum(weight) or n
    w = [max(int(total * x / s), 700) for x in weight]
    w[-1] += total - sum(w)
    return w


def image(path, rid):
    with open(path, "rb") as fh:
        head = fh.read(33)
    px_w, px_h = struct.unpack(">II", head[16:24])
    cx = TEXT_WIDTH_EMU
    cy = int(cx * px_h / px_w)
    return (
        f'<w:p><w:pPr><w:spacing w:line="{LINE}" w:lineRule="auto" '
        f'w:before="120" w:after="60"/><w:jc w:val="center"/><w:keepNext/></w:pPr>'
        f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" '
        f'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{rid[3:]}" name="{rid}"/>'
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{rid[3:]}" name="{rid}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        f'r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


# ────────────────────────────── разбор markdown ──────────────────────────────

def convert(md, images):
    """markdown -> (xml, список использованных картинок)"""
    out, used = [], []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # таблица
        if line.startswith("|") and i + 1 < len(lines) and re.match(r'^\|[\s\-|:]+\|$', lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r'^[\s\-|:]+$', "".join(cells)):
                    rows.append(cells)
                i += 1
            out.append(table(rows))
            out.append(para("", indent=False, after=120))
            continue

        # рисунок
        m = re.match(r'^!\[(.*?)\]\((.+?)\)$', line.strip())
        if m:
            path = (BODY / m.group(2)).resolve()
            rid = f"rId{900 + len(used)}"
            used.append((rid, path))
            out.append(image(path, rid))
            i += 1
            continue

        # подпись к рисунку
        if re.match(r'^Рисунок \d+ –', line.strip()):
            out.append(para(line.strip(), align="center", indent=False, after=200))
            i += 1
            continue

        # подпись к таблице
        if re.match(r'^Таблица \d+\.', line.strip()):
            buf = [line.strip()]
            while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("|"):
                i += 1
                buf.append(lines[i].strip())
            out.append(para(" ".join(buf), align="left", indent=False,
                            before=160, after=60, keep_next=True))
            i += 1
            continue

        # заголовки
        if line.startswith("### "):
            out.append(para(line[4:].strip(), align="center", indent=False,
                            bold=True, before=200, after=120, keep_next=True))
            i += 1
            continue
        if line.startswith("## "):
            out.append(para(line[3:].strip(), align="center", indent=False,
                            bold=True, before=240, after=140, keep_next=True))
            i += 1
            continue
        if line.startswith("# "):
            out.append(para(line[2:].strip(), align="center", indent=False,
                            bold=True, before=0, after=200,
                            page_break=True, keep_next=True))
            i += 1
            continue

        # цитата
        if line.startswith("> "):
            buf = []
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(lines[i][2:].strip())
                i += 1
            out.append(para(" ".join(buf), indent=False, before=120, after=120))
            continue

        # списки
        m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', line)
        if m:
            buf = []
            while i < len(lines):
                mm = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', lines[i].rstrip())
                if not mm:
                    if lines[i].startswith("  ") and lines[i].strip() and buf:
                        buf[-1] += " " + lines[i].strip()
                        i += 1
                        continue
                    break
                marker = mm.group(2)
                bullet = "— " if marker in ("-", "*") else marker + " "
                buf.append(bullet + mm.group(3).strip())
                i += 1
            for item in buf:
                out.append(para(item, indent=True, after=0))
            out.append(para("", indent=False, after=80))
            continue

        # обычный абзац
        buf = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r'^(#|\||!\[|> |\s*([-*]|\d+\.)\s|Таблица \d+\.|Рисунок \d+ –)', lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append(para(" ".join(buf)))
    return "".join(out), used


# ────────────────────────────── источники ──────────────────────────────

def strip_code(text):
    res, fence = [], False
    for ln in text.split("\n"):
        if ln.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            res.append(re.sub(r'`[^`]*`', '', ln))
    return "\n".join(res)


def renumber_sources(chapters):
    master = {}
    for ln in MASTER_SOURCES.read_text(encoding="utf-8").split("\n"):
        m = re.match(r'^(\d+)\.\s+(.*)$', ln)
        if m:
            master[int(m.group(1))] = m.group(2).strip()

    seen = []
    for md in chapters:
        for n in re.findall(r'\[(\d+)\]', strip_code(md)):
            n = int(n)
            if n not in seen:
                seen.append(n)
    unknown = [n for n in seen if n not in master]
    if unknown:
        sys.exit(f"ссылки на отсутствующие в перечне источники: {unknown}")

    mapping = {old: i + 1 for i, old in enumerate(seen)}
    out = []
    for md in chapters:
        res, fence = [], False
        for ln in md.split("\n"):
            if ln.lstrip().startswith("```"):
                fence = not fence
                res.append(ln)
                continue
            if fence:
                res.append(ln)
                continue
            spans = []

            def keep(m):
                spans.append(m.group(0))
                return f"\x00{len(spans) - 1}\x00"

            ln = re.sub(r'`[^`]*`', keep, ln)
            ln = re.sub(r'\[(\d+)\]', lambda m: f"[{mapping[int(m.group(1))]}]", ln)
            ln = re.sub(r'\x00(\d+)\x00', lambda m: spans[int(m.group(1))], ln)
            res.append(ln)
        out.append("\n".join(res))
    ordered = [master[old] for old in seen]
    return out, ordered


# ────────────────────────────── сборка docx ──────────────────────────────

def body_children(xml):
    """Грубая, но надёжная нарезка <w:body> на элементы верхнего уровня."""
    start = xml.index("<w:body>") + len("<w:body>")
    end = xml.rindex("</w:body>")
    inner, items, pos = xml[start:end], [], 0
    pat = re.compile(r'<w:(p|tbl|sectPr)\b')
    while pos < len(inner):
        m = pat.search(inner, pos)
        if not m:
            break
        tag = m.group(1)
        close = f"</w:{tag}>"
        if inner[m.start():].startswith(f"<w:{tag}/>"):
            stop = m.start() + len(f"<w:{tag}/>")
        else:
            stop = inner.index(close, m.start()) + len(close)
        items.append((m.start(), stop, tag, inner[m.start():stop]))
        pos = stop
    return xml[:start], items, xml[end:], inner


def text_of(chunk):
    return "".join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', chunk))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "Отчет.docx"))
    args = ap.parse_args()

    if not FORM.exists():
        sys.exit(f"форма не найдена: {FORM}")

    chapters = [p.read_text(encoding="utf-8") for p in sorted(BODY.glob("*.md"))]
    chapters, sources = renumber_sources(chapters)
    print(f"глав: {len(chapters)} | источников процитировано: {len(sources)}")

    xml_chapters, images = "", []
    for md in chapters:
        piece, used = convert(md, images)
        xml_chapters += piece
        images += used

    xml_sources = "".join(
        para(f"{i + 1}. {s}", align="left", indent=False, after=60)
        for i, s in enumerate(sources))

    with zipfile.ZipFile(FORM) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    head, items, tail, inner = body_children(doc)

    def find(pred):
        for idx, (_, _, tag, chunk) in enumerate(items):
            if tag == "p" and pred(text_of(chunk)):
                return idx
        return None

    i_start = find(lambda t: "Название главы зависит от задач" in t)
    i_end = find(lambda t: t.strip() == "Заключение")
    i_src = find(lambda t: t.strip() == "Список использованных источников")
    if None in (i_start, i_end, i_src) or not (i_start < i_end < i_src):
        sys.exit("не найдены опорные абзацы формы — разметка изменилась")

    new_items = []
    for idx, (_, _, tag, chunk) in enumerate(items):
        if i_start <= idx < i_end:                 # блок глав формы
            if idx == i_start:
                new_items.append(xml_chapters)
            continue
        if idx == i_src:                           # заголовок перечня сохраняем
            new_items.append(chunk)
            new_items.append(xml_sources)
            continue
        if idx > i_src and tag == "p" and text_of(chunk).strip():
            continue                               # примеры источников из формы
        new_items.append(chunk)

    doc_new = head + "".join(new_items) + tail
    parts["word/document.xml"] = doc_new.encode("utf-8")

    # картинки: часть + связь + тип содержимого
    rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
    add_rels = ""
    for rid, path in images:
        name = f"media/{rid}.png"
        parts[f"word/{name}"] = pathlib.Path(path).read_bytes()
        add_rels += (f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                     f'officeDocument/2006/relationships/image" Target="{name}"/>')
    parts["word/_rels/document.xml.rels"] = rels.replace(
        "</Relationships>", add_rels + "</Relationships>").encode("utf-8")

    ct = parts["[Content_Types].xml"].decode("utf-8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Types ", '<Types ', 1).replace(
            "</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
    parts["[Content_Types].xml"] = ct.encode("utf-8")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    print(f"записано: {out}  ({out.stat().st_size // 1024} КБ, картинок: {len(images)})")


if __name__ == "__main__":
    main()
