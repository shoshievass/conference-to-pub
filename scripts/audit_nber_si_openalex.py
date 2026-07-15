#!/usr/bin/env python3
"""Cross-check every unresolved renamed-lineage candidate in OpenAlex.

DOIs are queried in batches so the full candidate universe costs only a small
number of metadata requests. OpenAlex abstracts and the first pages of the SI
draft are used as review evidence; neither source automatically changes status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from audit_nber_si_cvs import match_norm
from audit_nber_si_renamed_lineages import (
    STOPWORDS,
    fetch_first_pages_text,
    title_history_notes,
)
from nber_si_audit_common import lineage_id_for_row


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nber_si" / "data"
CACHE = ROOT / "nber_si" / "cache" / "openalex"


def load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def reconstruct_abstract(index: dict | None) -> str:
    if not index:
        return ""
    positions = [(position, word) for word, offsets in index.items() for position in offsets]
    return " ".join(word for _, word in sorted(positions))


def content_terms(text: str) -> list[str]:
    return [token for token in match_norm(text).split()
            if len(token) >= 3 and token not in STOPWORDS and not token.isdigit()]


def cosine_similarity(left: str, right: str) -> float | None:
    a, b = Counter(content_terms(left)), Counter(content_terms(right))
    if len(a) < 8 or len(b) < 8:
        return None
    overlap = set(a) & set(b)
    numerator = sum((1 + math.log(a[t])) * (1 + math.log(b[t])) for t in overlap)
    a_norm = math.sqrt(sum((1 + math.log(value)) ** 2 for value in a.values()))
    b_norm = math.sqrt(sum((1 + math.log(value)) ** 2 for value in b.values()))
    return numerator / (a_norm * b_norm) if a_norm and b_norm else None


def batch_url(dois: list[str]) -> str:
    normalized = [doi.lower().removeprefix("https://doi.org/") for doi in dois]
    params = {
        "filter": "doi:" + "|".join(normalized),
        "per-page": "100",
        "select": (
            "id,doi,title,publication_year,publication_date,type,primary_location,"
            "authorships,abstract_inverted_index,locations"
        ),
    }
    return "https://api.openalex.org/works?" + urllib.parse.urlencode(params, safe="|:,/")


def fetch_batch(dois: list[str], refresh: bool, retries: int = 3) -> dict:
    url = batch_url(dois)
    path = CACHE / "batches" / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if path.exists() and not refresh:
        cached = load(path, {})
        if not cached.get("error"):
            return cached
    path.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "conference-to-pub/1.0 (academic research audit)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read())
            out = {"query_url": url, "results": payload.get("results", [])}
            path.write_text(json.dumps(out, ensure_ascii=False))
            return out
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = str(exc)
            time.sleep(1.5 * (attempt + 1))
    out = {"query_url": url, "results": [], "error": last}
    path.write_text(json.dumps(out, ensure_ascii=False))
    return out


def openalex_journal(work: dict) -> str | None:
    source = ((work.get("primary_location") or {}).get("source") or {})
    return source.get("display_name")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--pdf", action="store_true", help="fetch/check first pages for every candidate lineage")
    parser.add_argument("--output", default="nber_si/data/openalex_audit_candidates.json")
    args = parser.parse_args()

    papers = load(DATA / "papers_enriched.json", [])
    by_id = {row["id"]: row for row in papers}
    candidates = load(DATA / "renamed_lineage_candidates.json", [])
    candidates = [candidate for candidate in candidates
                  if candidate.get("doi")
                  and by_id.get(candidate.get("paper_id"), {}).get("status") == "working_paper"]
    dois = sorted({candidate["doi"].lower().removeprefix("https://doi.org/") for candidate in candidates})

    works_by_doi = {}
    failed_batches = 0
    for offset in range(0, len(dois), args.batch_size):
        batch = dois[offset:offset + args.batch_size]
        result = fetch_batch(batch, args.refresh)
        if result.get("error"):
            failed_batches += 1
        for work in result.get("results") or []:
            doi = (work.get("doi") or "").lower().removeprefix("https://doi.org/")
            if doi:
                works_by_doi[doi] = work
        print(f"openalex {min(offset + len(batch), len(dois))}/{len(dois)}", flush=True)

    by_lineage = defaultdict(list)
    for candidate in candidates:
        paper = by_id[candidate["paper_id"]]
        lineage_id = lineage_id_for_row(paper)
        doi = candidate["doi"].lower().removeprefix("https://doi.org/")
        work = works_by_doi.get(doi) or {}
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
        pdf_text = fetch_first_pages_text(paper.get("paper_url"), args.refresh) if args.pdf else ""
        similarity = cosine_similarity(pdf_text, abstract) if pdf_text and abstract else None
        notes = title_history_notes(pdf_text, paper["title"], candidate["candidate_title"]) if pdf_text else []
        by_lineage[lineage_id].append({
            "paper_id": candidate["paper_id"],
            "agenda_title": candidate["agenda_title"],
            "candidate_title": candidate["candidate_title"],
            "doi": doi,
            "crossref_journal": candidate.get("journal"),
            "openalex_journal": openalex_journal(work),
            "publication_year": work.get("publication_year") or candidate.get("candidate_year"),
            "openalex_id": work.get("id"),
            "openalex_type": work.get("type"),
            "openalex_found": bool(work),
            "abstract_available": bool(abstract),
            "agenda_pdf_checked": bool(args.pdf),
            "agenda_pdf_available": bool(pdf_text and "FETCH_ERROR" not in pdf_text),
            "abstract_similarity": round(similarity, 3) if similarity is not None else None,
            "pdf_title_history_notes": notes,
            "title_ratio": candidate.get("title_ratio"),
            "distinctive_term_coverage": candidate.get("distinctive_term_coverage"),
            "review_state": (
                "strong_semantic_lineage" if similarity is not None and similarity >= 0.35
                else "strong_title_history_note" if notes
                else "metadata_cross_checked_needs_decision"
            ),
        })

    output = ROOT / args.output
    prior = load(output, {})
    for lineage_id, rows in by_lineage.items():
        prior[lineage_id] = {
            "lineage_id": lineage_id,
            "title": rows[0]["agenda_title"],
            "state": "complete" if not failed_batches else "pending",
            "checked": len(rows),
            "pdf_checked": sum(row["agenda_pdf_checked"] for row in rows),
            "openalex_found": sum(row["openalex_found"] for row in rows),
            "abstracts": sum(row["abstract_available"] for row in rows),
            "strong_semantic_matches": sum(row["review_state"] == "strong_semantic_lineage" for row in rows),
            "candidates": rows,
            "checked_at": "2026-07-14",
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(prior, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "candidate_rows": len(candidates),
        "candidate_lineages": len(by_lineage),
        "unique_dois": len(dois),
        "openalex_records": len(works_by_doi),
        "failed_batches": failed_batches,
        "abstracts": sum(item["abstracts"] for item in prior.values()),
        "strong_semantic_matches": sum(item["strong_semantic_matches"] for item in prior.values()),
        "output": str(output.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
