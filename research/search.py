#!/usr/bin/env python3
"""
Reproducible literature search behind report section 3.1.

Runs the documented query set against the Crossref and arXiv APIs, writes every
retrieved record to candidates.tsv, and prints the selection funnel. The point is
that the review's numbers can be regenerated rather than taken on trust:

    python3 research/search.py            # run the full query set
    python3 research/search.py --stats    # funnel from the existing candidates.tsv

Screening (venue quality, topical relevance) stays a human judgement and is
recorded in included.txt -- one DOI or arXiv id per line, with the cluster it
was assigned to.
"""
import argparse
import csv
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
CANDIDATES = HERE / "candidates.tsv"
INCLUDED = HERE / "included.txt"
UA = "practice-report/1.0"

MIN_YEAR = 2021
CROSSREF_TYPES = {"journal-article", "proceedings-article", "book-chapter"}

# --- the documented query set ------------------------------------------------
# Grouped by the taxonomy cluster each query is meant to populate (report 3.2).
QUERIES = {
    "K1 forecasting": [
        "Kubernetes resource request right-sizing machine learning",
        "predicting resource consumption Kubernetes container systems",
        "cloud workload prediction machine learning survey",
        "quantile regression resource allocation SLA cloud",
    ],
    "K2 resource management": [
        "vertical pod autoscaler resource recommendation",
        "Kubernetes horizontal pod autoscaler SLA threshold",
        "elastic resource provisioning microservices cluster",
    ],
    "K3 scheduling": [
        "Kubernetes scheduler simulator evaluation",
        "container bin packing placement energy efficiency cluster",
        "reinforcement learning Kubernetes job scheduler",
    ],
    "K4 simulation": [
        "CloudSim simulation framework cloud computing environments",
        "discrete event simulation cluster scheduling",
        "cluster trace analysis Alibaba Google resource over-provisioning",
    ],
    "K5 continuous integration": [
        "continuous integration build duration optimization empirical study",
        "continuous integration build failure prediction machine learning",
        "test case selection prioritization continuous integration cost reduction",
        "CI/CD pipeline cost cloud resource optimization",
    ],
    "K6 economics and sustainability": [
        "FinOps cloud cost optimization",
        "carbon aware scheduling datacenter",
        "infrastructure as code technical debt quantitative",
    ],
}

ARXIV_QUERIES = [
    "Kubernetes rightsizing resource requests",
    "continuous integration build resources cost",
    "Kubernetes scheduling simulator",
    "microservice resource prediction autoscaling",
    "FinOps cloud cost optimization engineering",
    "carbon aware scheduling datacenter",
    "cluster trace characterization workload",
    "serverless resource allocation",
]


def curl(url):
    return subprocess.run(["curl", "-sS", "--max-time", "45", "-A", UA, url],
                          capture_output=True, check=True).stdout


def crossref(query, rows=8):
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": query, "rows": rows,
        "select": "DOI,title,author,container-title,issued,type,published-print,published-online",
    })
    for item in json.loads(curl(url))["message"]["items"]:
        year = None
        for key in ("published-print", "published-online", "issued"):
            parts = item.get(key, {}).get("date-parts", [[None]])[0]
            if parts and parts[0]:
                year = parts[0]
                break
        authors = item.get("author") or []
        yield {
            "source": "crossref",
            "id": item["DOI"],
            "year": year or "",
            "type": item.get("type", ""),
            "title": (item.get("title") or [""])[0].strip(),
            "authors": "; ".join(
                f"{a.get('family','')} {a.get('given','')[:1]}." for a in authors if a.get("family")),
            "venue": (item.get("container-title") or [""])[0],
        }


def arxiv(query, rows=8):
    expr = " AND ".join(f"all:{w}" for w in query.split())
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": expr, "start": 0, "max_results": rows,
        "sortBy": "relevance", "sortOrder": "descending",
    })
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in ET.fromstring(curl(url)).findall("a:entry", ns):
        published = entry.findtext("a:published", "", ns)[:10]
        aid = entry.findtext("a:id", "", ns).rsplit("/", 1)[-1]
        yield {
            "source": "arxiv",
            "id": re.sub(r"v\d+$", "", aid),
            "year": published[:4],
            "type": "preprint",
            "title": " ".join(entry.findtext("a:title", "", ns).split()),
            "authors": "; ".join(a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)),
            "venue": " ".join((entry.findtext("a:journal_ref", "", ns) or "").split()),
        }


def run():
    rows, retrieved = {}, 0
    for cluster, queries in QUERIES.items():
        for q in queries:
            print(f"crossref | {cluster:32} | {q}", file=sys.stderr)
            for rec in crossref(q):
                retrieved += 1
                rec["cluster"], rec["query"] = cluster, q
                rows.setdefault(rec["id"], rec)
            time.sleep(0.6)
    for q in ARXIV_QUERIES:
        print(f"arxiv    | {'':32} | {q}", file=sys.stderr)
        for rec in arxiv(q):
            retrieved += 1
            rec["cluster"], rec["query"] = "arxiv", q
            rows.setdefault(rec["id"], rec)
        time.sleep(3)

    fields = ["source", "id", "year", "type", "title", "authors", "venue", "cluster", "query"]
    with CANDIDATES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for rec in sorted(rows.values(), key=lambda r: (r["source"], str(r["year"]))):
            w.writerow(rec)
    print(f"\nretrieved records: {retrieved}")
    print(f"unique after dedup: {len(rows)}  -> {CANDIDATES.name}")
    stats()


def stats():
    if not CANDIDATES.exists():
        sys.exit(f"{CANDIDATES} not found -- run without --stats first")
    with CANDIDATES.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    def year_ok(r):
        return r["year"].isdigit() and int(r["year"]) >= MIN_YEAR

    typed = [r for r in rows if r["source"] == "arxiv" or r["type"] in CROSSREF_TYPES]
    recent = [r for r in typed if year_ok(r)]
    included = set()
    if INCLUDED.exists():
        included = {ln.split("#")[0].strip() for ln in INCLUDED.read_text(encoding="utf-8").splitlines()
                    if ln.split("#")[0].strip()}

    print(f"\n{'unique candidates':32} {len(rows):>4}")
    print(f"{'  of publication type':32} {len(typed):>4}")
    print(f"{f'  published {MIN_YEAR} or later':32} {len(recent):>4}")
    print(f"{'  included after screening':32} {len(included):>4}")
    queries = len({r["query"] for r in rows})
    print(f"\nqueries issued: {queries}  (crossref + arxiv)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="report the funnel without querying")
    if ap.parse_args().stats:
        stats()
    else:
        run()
