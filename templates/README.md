# templates

Export styling, kept in version control instead of in someone's Word session.

| File | Used by | Effect |
|---|---|---|
| `report-template.docx` | `make docx` | paragraph/heading styles, margins, page setup applied to the exported report |
| `report-template.css` | `make pdf` | typography and page rules for the PDF renderer |

Both are optional. When a file is absent the stage warns and falls back to
Gramax defaults, so the pipeline stays green on a fresh clone.

## The DOCX template

Gramax maps the report's structure onto the template's **named styles**, so the
template is an ordinary `.docx` whose styles have been redefined — not a document
with content in it.

These are the styles the current report actually emits, read back out of a
built `artifacts/report.docx` rather than guessed. Note that article titles and
in-article headings use **two different naming schemes** — redefining only
`Heading1`/`Heading2` leaves every subsection unstyled:

| Style | Comes from | Count in the current report |
|---|---|---|
| `Title` | the catalog root article | 1 |
| `Heading1` | a top-level article's front-matter `title` | 6 |
| `Heading2` | a nested article's front-matter `title` | 11 |
| `H2` | a body `##` heading | 76 |
| `H3` | a body `###` heading | 2 |
| `ListParagraph` | bullet and numbered lists | 112 |
| `Formula` | a `$$…$$` block | 2 |
| `Fence` | a fenced code block | 2 |

Re-read them after any structural change:

```bash
make docx && python3 -c "
import re, zipfile, collections
xml = zipfile.ZipFile('artifacts/report.docx').read('word/document.xml').decode()
print(collections.Counter(re.findall(r'<w:pStyle w:val=\"([^\"]+)\"/>', xml)).most_common())"
```

To build a template from the department's form:

1. Open the form in Word/LibreOffice and delete its body text.
2. Redefine the styles listed above, plus `Normal` and the table style.
3. Set page size and margins on the section (GOST 7.32 typically wants
   left 30 mm, right 10 mm, top/bottom 20 mm; Times New Roman 14 pt; 1.5 line
   spacing; first-line indent 1.25 cm).
4. Save as `templates/report-template.docx` and run `make docx`.

Verify against the real output rather than the template — `artifacts/report.docx`
is what gets handed in:

```bash
make docx && libreoffice --headless --convert-to pdf artifacts/report.docx
```

The title page, signature blocks and any other fixed front matter belong in
`report/_index.md`, not in the template: the export replaces the template's body.
