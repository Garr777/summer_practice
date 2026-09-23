# summer-practice — research report, built as code

The practice report ("Отчёт по летней практике") written the way the software it
describes is written: Markdown in Git, a pipeline that validates it, and the
submitted documents produced by a build rather than by editing a Word file.

The report itself is in Russian (it is handed in to a Russian department);
everything around it — this README, `ci/`, commit messages, branch names — is in
English, matching the two projects the research is about.

## Two editions, one source

| Edition | Source | Output | Purpose |
|---|---|---|---|
| Full (~50 pages) | `report/` | `artifacts/report.docx`, `report.pdf`, `site/` | groundwork for the thesis |
| Condensed (~17 pages) | `kfu/body/` | `artifacts/Отчет.docx` | what gets submitted, written into the department's form |

Both cite the same bibliography, `report/5-istochniki.md`. The condensed edition
carries the full report's citation numbers and the build renumbers them by first
mention, so the two cannot drift apart in their numbering.

## Layout

| Path | Role |
|---|---|
| `report/` | the Gramax catalog: the full report, one `.md` per section |
| `report/.doc-root.yaml` | catalog settings (title, language, properties) |
| `report/images/` | figures: SVG source plus the generated PNG |
| `kfu/body/` | the condensed edition for submission |
| `kfu/build_report.py` | writes that edition into the department's `.docx` form |
| `research/` | the literature search: query set, retrieved records, included ids |
| `ci/` | the pipeline — one script per stage, runnable individually |
| `templates/` | DOCX/PDF templates the export renders through |
| `artifacts/` | build output (git-ignored) |
| `workspace.yaml` | Gramax workspace config |
| `practice-1.pdf` | the assignment brief, kept for reference |

The department's form itself is **not** in this repository. Put it at
`Practice_docs/Отчет.docx` and the `kfu` stage will fill it; without it that
stage warns and skips, so a fresh clone still builds.

## Requirements

- **Node.js 18+** — `gramax-cli` runs through `npx`, nothing to install globally.
- **Python 3.10+** — the figure rasteriser, the form filler and the literature search.
- **Bash 4+**, **GNU coreutils**, **make** — the pipeline scripts.
- Optional: `rsvg-convert` or `python3-cairosvg` to regenerate diagrams. Without
  either, the committed PNGs are used and the stage refuses to ship a PNG older
  than its SVG.

No network access is needed after the first `npx` download, which caches the CLI.
The CLI version is pinned in `ci/lib.sh` (`GRAMAX_CLI_VERSION`) so a report that
builds today builds the same way next term. Override it for a one-off run:

```bash
GRAMAX_CLI_VERSION=1.0.54 make all
```

## Build

```bash
make all        # full pipeline -> artifacts/
```

Individual stages, in the order the pipeline runs them:

```bash
make lint       # front matter, duplicate ordering, leftover TODOs
make figures    # rasterise diagrams: report/images/*.svg -> *.png
make check      # gramax catalog validation (links, images, unsupported elements)
make sources    # bibliography gate: >= 30 entries, recency, citation coverage
make html       # static site           -> artifacts/site/
make docx       # full edition          -> artifacts/report.docx
make pdf        # reading copy          -> artifacts/report.pdf
make kfu        # department's form     -> artifacts/Отчет.docx
make serve      # preview the site on http://127.0.0.1:8080
make clean      # drop artifacts/ and ci/logs/
```

`make stages` lists the targets. Each stage is also a standalone script —
`ci/30_sources.sh` runs on its own — and `ci/pipeline.sh lint check` runs a
chosen subset. Every stage writes its raw tool output to `ci/logs/<stage>.log`,
which is where to look when one fails.

To regenerate the literature-search funnel reported in the review:

```bash
python3 research/search.py           # re-run the query set
python3 research/search.py --stats   # funnel from the existing records
```

## Why there is a `ci/` and not just a CI file

There is no CI server for this repository, so `ci/` imitates one: the same stage
boundaries, the same fail-fast gate, the same `artifacts/` directory a runner
would publish. `.gitlab-ci.yml` mirrors it by *calling the same scripts*, so the
local run and the hosted run cannot drift apart — the YAML has no build logic of
its own.

Three stages exist to automate rules that are otherwise checked by hand on every
revision:

- **`lint`** — an article with no front matter renders with its filename as a
  heading, and two sections sharing an `order` come out shuffled. Both are
  invisible in Markdown and obvious only in the handed-in DOCX.
- **`sources`** — the brief requires at least 30 sources from the last 3–5 years,
  each actually cited. The check runs both ways: a citation past the end of the
  bibliography fails the build, an uncited entry warns.
- **`figures`** — diagrams are authored as SVG so they stay text, but gramax
  embeds a referenced `.svg` into the DOCX as raw SVG bytes under a `.png` part
  name, which Word cannot draw. Articles therefore reference the PNG, this stage
  regenerates it, and the export verifies every embedded image's magic bytes
  match its declared extension.

## Editing

Any editor works — the source is plain Markdown with YAML front matter:

```markdown
---
title: Введение
order: 1
---

Текст раздела.
```

The front-matter `title` becomes the heading, so do not repeat it as an H1 in the
body: `lint` rejects that, because the export would print the title twice.

For a WYSIWYG view of the same files, open the repository as a workspace in
[Gramax](https://gram.ax/ru) (desktop or web). It reads and writes this layout
directly and commits through Git, so both ways of editing stay interchangeable.

## Templates

`make docx` renders through `templates/report-template.docx` when that file
exists, and falls back to Gramax defaults (with a warning) when it does not.
`make pdf` picks up `templates/report-template.css` the same way. See
[`templates/README.md`](templates/README.md) — it lists the paragraph styles the
export actually emits, which is not the set you would guess.

`make kfu` does not use those templates: it applies direct formatting per
paragraph (Times New Roman 14, 1.5 spacing, 1.25 cm indent) so the result does
not depend on the form's own styles.

## Branches

`main` holds reviewed work. Sections are written on `docs/<section>` branches and
merged when the pipeline is green — the history is meant to show how the report
was assembled, not to arrive as one commit.
