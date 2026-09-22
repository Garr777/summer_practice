# summer-practice — research report, built as code

The practice report ("Отчёт по летней практике") written the way the software it
describes is written: Markdown in Git, a pipeline that validates it, and
`artifacts/report.docx` produced by a build rather than by editing a Word file.

The report itself is in Russian (it is handed in to a Russian department);
everything around it — this README, `ci/`, commit messages, branch names — is in
English, matching the two projects the research is about.

| Path | Role |
|---|---|
| `report/` | the Gramax catalog: the report's source, one `.md` per section |
| `report/.doc-root.yaml` | catalog settings (title, language, properties) |
| `ci/` | the pipeline — one script per stage, runnable individually |
| `templates/` | DOCX/PDF templates the export renders through |
| `artifacts/` | build output (git-ignored): `site/`, `report.docx`, `report.pdf` |
| `workspace.yaml` | Gramax workspace config |
| `practice-1.pdf` | the assignment brief, kept for reference |

## Requirements

- **Node.js 18+** — `gramax-cli` runs through `npx`, nothing to install globally.
- **Bash 4+**, **GNU coreutils**, **make** — the pipeline scripts.
- No network access is needed after the first `npx` download, which caches the CLI.

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
make html       # static site        -> artifacts/site/
make docx       # the deliverable    -> artifacts/report.docx
make pdf        # reading copy       -> artifacts/report.pdf
make serve      # preview the site on http://127.0.0.1:8080
make clean      # drop artifacts/ and ci/logs/
```

`make stages` lists the targets. Each stage is also a standalone script —
`ci/30_sources.sh` runs on its own — and every stage writes its raw tool output
to `ci/logs/<stage>.log`, which is where to look when one fails.

## Why there is a `ci/` and not just a CI file

There is no CI server for this repository, so `ci/` imitates one: the same stage
boundaries, the same fail-fast gate, the same `artifacts/` directory a runner
would publish. `.gitlab-ci.yml` mirrors it by *calling the same scripts*, so the
local run and the hosted run cannot drift apart — the YAML has no build logic of
its own.

Two of the stages exist purely to automate rules from the assignment brief:

- **`lint`** — an article with no front matter renders with its filename as a
  heading, and two sections sharing an `order` come out shuffled. Both are
  invisible in Markdown and obvious only in the handed-in DOCX.
- **`sources`** — the brief requires at least 30 sources from the last 3–5 years,
  each actually cited. Re-counting that by hand on every revision is the
  monotonous work this approach is meant to remove.
- **`figures`** — diagrams are authored as SVG so they stay text, but gramax
  embeds a referenced `.svg` into the DOCX as raw SVG bytes under a `.png` part
  name, which Word cannot draw. Articles therefore reference the PNG, this
  stage regenerates it, and `export:docx` verifies every embedded image's magic
  bytes match its declared extension.

## Editing

Any editor works — the source is plain Markdown with YAML front matter:

```markdown
---
title: Введение
order: 1
---

# Введение
```

For a WYSIWYG view of the same files, open the repository as a workspace in
[Gramax](https://gram.ax/ru) (desktop or web). It reads and writes this layout
directly and commits through Git, so both ways of editing stay interchangeable.

## Templates

`make docx` renders through `templates/report-template.docx` when that file
exists, and falls back to Gramax defaults (with a warning) when it does not —
put the department's form there to have the deliverable come out already styled.
`make pdf` picks up `templates/report-template.css` the same way. See
[`templates/README.md`](templates/README.md).

## Branches

`main` holds reviewed work. Sections are written on `docs/<section>` branches and
merged when the pipeline is green — the history is meant to show how the report
was assembled, not to arrive as one commit.
