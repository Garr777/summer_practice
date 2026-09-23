# Front-end for ci/. Every target is one pipeline stage, so what runs locally
# and what a runner would run are the same scripts.
.PHONY: all lint figures check sources html docx pdf kfu clean serve stages

all:      ## run the full pipeline (lint -> check -> sources -> html -> docx -> pdf)
	@ci/pipeline.sh

lint:     ## structural lint of the catalog
	@ci/pipeline.sh lint

figures:  ## rasterise report/images/*.svg to the PNGs the export ships
	@ci/pipeline.sh figures

check:    ## gramax catalog validation
	@ci/pipeline.sh check

sources:  ## bibliography gate (>= 30 sources, recency, citation coverage)
	@ci/pipeline.sh sources

html:     ## build the static site -> artifacts/site
	@ci/pipeline.sh build:html

docx:     ## export the deliverable -> artifacts/report.docx
	@ci/pipeline.sh export:docx

pdf:      ## export the reading copy -> artifacts/report.pdf
	@ci/pipeline.sh export:pdf

kfu:      ## fill the department's form -> artifacts/Отчет.docx
	@ci/pipeline.sh export:kfu

serve:    ## preview the built site on :8080
	@python3 -m http.server 8080 --directory artifacts/site

clean:    ## drop artifacts and stage logs
	@rm -rf artifacts ci/logs
	@echo "cleaned"

stages:   ## list available targets
	@grep -E '^[a-z:]+:.*##' $(MAKEFILE_LIST) \
		| sed 's/:.*##/\t/' | expand -t 12
