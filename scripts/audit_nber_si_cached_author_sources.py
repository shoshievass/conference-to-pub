#!/usr/bin/env python3
"""Scan cached author pages/CVs for missed NBER SI publication/R&R statuses.

This script is intentionally cache-only: it does not fetch new pages. It is meant
to find review candidates among provisional NBER SI rows using author pages and
documents already discovered by ``audit_nber_si_cvs.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_nber_si_cvs import (  # noqa: E402
    cache_path,
    direct_document_url,
    evidence_on_page,
    match_norm,
)


ROOT = Path(__file__).resolve().parents[1]


def title_rank(rows: list[dict]) -> tuple:
    return (-max(row["year"] for row in rows), -len(rows), rows[0]["title"].casefold())


def cached_page(url: str, kind: str) -> str | None:
    if kind == "document":
        path = cache_path("document_text", direct_document_url(url), ".txt")
        if not path.exists():
            return None
        text = path.read_text(errors="replace")
        if "FETCH_ERROR" in text:
            return None
        return "<pre>" + text + "</pre>"
    path = cache_path("external_pages", url)
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    if "FETCH_ERROR" in text:
        return None
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--documents-per-author", type=int, default=8)
    parser.add_argument("--output", default="nber_si/data/cached_author_source_candidates.json")
    args = parser.parse_args()

    data = ROOT / "nber_si" / "data"
    rows = json.loads((data / "papers_enriched.json").read_text())
    sources = json.loads((data / "cv_audit_sources.json").read_text())
    source_by_name = {source.get("name"): source for source in sources}

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("status") == "working_paper" and row.get("verification") == "provisional":
            grouped.setdefault(match_norm(row["title"]), []).append(row)
    lineages = sorted(grouped.values(), key=title_rank)
    if args.offset:
        lineages = lineages[args.offset:]
    if args.limit:
        lineages = lineages[:args.limit]

    candidates = []
    seen = set()
    scanned = skipped = 0
    for n, title_rows in enumerate(lineages, 1):
        sibling_titles = [row["title"] for row in title_rows]
        for profile in title_rows[0].get("author_profiles") or []:
            author = profile.get("name")
            source = source_by_name.get(author) or {}
            sources_to_scan = [
                ("page", page["url"]) for page in source.get("external_pages", [])
            ]
            sources_to_scan.extend(
                ("document", document["url"])
                for document in source.get("likely_documents", [])[:args.documents_per_author]
            )
            for kind, url in sources_to_scan:
                page = cached_page(url, "document" if kind == "document" else "page")
                if page is None:
                    skipped += 1
                    continue
                scanned += 1
                for row in title_rows:
                    evidence = evidence_on_page(page, url, row, sibling_titles)
                    if not evidence:
                        continue
                    evidence["author"] = author
                    evidence["source_kind"] = kind
                    evidence["lineage_rank"] = args.offset + n
                    key = (
                        evidence["paper_id"],
                        evidence["candidate_status"],
                        evidence["journal"],
                        evidence["evidence_url"],
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(evidence)
        if n % 100 == 0:
            print(
                f"  scanned lineages {n}/{len(lineages)}; "
                f"sources {scanned}; candidates {len(candidates)}",
                flush=True,
            )

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(output.read_text()) if output.exists() else []
    merged = list({
        (
            row.get("paper_id"),
            row.get("candidate_status"),
            row.get("journal"),
            row.get("evidence_url"),
        ): row
        for row in [*existing, *candidates]
    }.values())
    output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "lineages": len(lineages),
        "offset": args.offset,
        "cached_sources_scanned": scanned,
        "uncached_or_error_sources_skipped": skipped,
        "new_candidates_this_run": len(candidates),
        "merged_candidates": len(merged),
        "output": str(output.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
