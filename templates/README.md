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
with content in it. To build one from the department's form:

1. Open the form in Word/LibreOffice and delete its body text.
2. Redefine the styles the export uses: `Normal`, `Heading 1`–`Heading 4`,
   `Caption`, `Table Grid`, `List Paragraph`, `Quote`, `Source Code`.
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
