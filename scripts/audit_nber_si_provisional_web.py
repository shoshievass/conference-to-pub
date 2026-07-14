#!/usr/bin/env python3
"""Search the open web for status evidence on unresolved NBER SI papers.

This is a candidate generator, not an automatic classifier. It targets the
remaining ``verification=provisional`` working-paper rows and searches exact
paper titles plus coauthor/status terms. Any candidates it finds still flow
through the curated author-source audit before changing dashboard status.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_nber_si_cvs import (  # noqa: E402
    direct_document_url,
    evidence_on_page,
    fetch,
    fetch_document,
    is_blocked_source_url,
    likely_documents,
    match_norm,
    search_duckduckgo,
    visible_text,
)


ROOT = Path(__file__).resolve().parents[1]


def title_queries(title: str, authors: list[str], max_authors: int, status_queries: bool) -> list[str]:
    """Queries designed to surface author pages and status snippets."""
    queries = [f'"{title}"']
    if status_queries:
        queries.extend([
            f'"{title}" "revise and resubmit"',
            f'"{title}" "forthcoming"',
            f'"{title}" "accepted"',
        ])
    for author in authors[:max_authors]:
        queries.append(f'"{title}" "{author}"')
    return queries


def title_priority(rows: list[dict]) -> tuple:
    """Recent and repeated lineages are most likely to have stale provisional labels."""
    years = [row["year"] for row in rows]
    return (-max(years), -len(rows), rows[0]["title"].casefold())


def source_rank(url: str) -> int:
    """Prefer pages likely to be author-controlled or institutional."""
    host = re.sub(r"^www\.", "", re.sub(r":.*$", "", __import__("urllib.parse").parse.urlparse(url).netloc.lower()))
    path = __import__("urllib.parse").parse.urlparse(url).path.lower()
    if "github.io" in host or "sites.google.com" in host or "faculty" in host or "economics" in host:
        return 0
    if re.search(r"\b(cv|research|papers?|publications?)\b", path):
        return 1
    if host.endswith(".edu") or ".edu." in host:
        return 2
    return 3


def discover_title_pages(
    title: str,
    authors: list[str],
    refresh: bool,
    max_results: int,
    max_authors: int,
    status_queries: bool,
    timeout: int,
    cache_only: bool,
) -> list[dict]:
    pages, seen = [], set()
    for query in title_queries(title, authors, max_authors, status_queries):
        for result in search_duckduckgo(
            query,
            refresh=refresh,
            max_results=max_results,
            timeout=timeout,
            cache_only=cache_only,
        ):
            url = result["url"].rstrip("/")
            if url in seen or is_blocked_source_url(url):
                continue
            seen.add(url)
            pages.append(result)
    pages.sort(key=lambda row: (source_rank(row["url"]), row["url"]))
    return pages


def scan_page(page_url: str, page: str, rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    candidates, title_seen, docs = [], [], []
    sibling_titles = [row["title"] for row in rows]
    page_text = visible_text(page)
    normalized_page = match_norm(page_text)
    for row in rows:
        paper_title = match_norm(row["title"])
        if len(paper_title.split()) >= 4 and paper_title in normalized_page:
            title_seen.append({
                "paper_id": row["id"],
                "title": row["title"],
                "evidence_url": page_url,
            })
        evidence = evidence_on_page(page, page_url, row, sibling_titles)
        if evidence:
            evidence["discovery"] = "title_web_search"
            candidates.append(evidence)
    docs.extend(likely_documents(page, page_url))
    return candidates, title_seen, docs


def existing_keys(path: Path) -> set[tuple]:
    if not path.exists():
        return set()
    return {
        (row.get("paper_id"), row.get("candidate_status"), row.get("journal"), row.get("evidence_url"))
        for row in json.loads(path.read_text())
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-results", type=int, default=4)
    parser.add_argument("--max-authors", type=int, default=2)
    parser.add_argument("--search-timeout", type=int, default=8)
    parser.add_argument("--status-queries", action="store_true",
                        help="also search exact title with accepted/forthcoming/R&R phrases")
    parser.add_argument("--cache-only", action="store_true",
                        help="parse cached search results without issuing new search requests")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--output", default="nber_si/data/provisional_web_audit_candidates.json")
    args = parser.parse_args()

    rows = json.loads((ROOT / "nber_si" / "data" / "papers_enriched.json").read_text())
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("status") == "working_paper" and row.get("verification") == "provisional":
            grouped[match_norm(row["title"])].append(row)

    lineages = sorted(grouped.values(), key=title_priority)
    if args.offset:
        lineages = lineages[args.offset:]
    if args.limit:
        lineages = lineages[:args.limit]

    print(f"Provisional lineages queued: {len(lineages)} (offset {args.offset})", flush=True)
    all_pages: dict[str, dict] = {}
    query_log = []
    for n, title_rows in enumerate(lineages, 1):
        title = title_rows[0]["title"]
        authors = title_rows[0].get("authors_list") or []
        pages = discover_title_pages(
            title, authors, args.refresh, args.max_results, args.max_authors,
            args.status_queries, args.search_timeout, args.cache_only,
        )
        query_log.append({
            "title": title,
            "paper_ids": [row["id"] for row in title_rows],
            "pages": pages,
        })
        for page in pages[:8]:
            all_pages.setdefault(page["url"].rstrip("/"), page)
        if n % 25 == 0:
            print(f"  searched {n}/{len(lineages)}; unique pages {len(all_pages)}", flush=True)

    print(f"Fetching candidate pages: {len(all_pages)}", flush=True)
    page_bodies: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch, url, "provisional_web_pages", args.refresh): url for url in all_pages}
        for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
            page_bodies[futures[future]] = future.result()
            if n % 100 == 0:
                print(f"  pages {n}/{len(futures)}", flush=True)

    candidates, title_seen, docs_by_url = [], [], {}
    title_to_rows = {rows[0]["title"]: rows for rows in lineages}
    for logged in query_log:
        rows_for_title = title_to_rows[logged["title"]]
        for page in logged["pages"][:8]:
            url = page["url"].rstrip("/")
            found, seen, docs = scan_page(url, page_bodies.get(url, ""), rows_for_title)
            candidates.extend(found)
            title_seen.extend(seen)
            for doc in docs:
                doc_url = direct_document_url(doc["url"])
                docs_by_url.setdefault(doc_url, doc)

    strong_docs = [
        doc for doc in docs_by_url.values()
        if re.search(r"\b(cv|curriculum|vitae|vita|research|publications?)\b",
                     (doc.get("url") or "") + " " + (doc.get("text") or ""), re.I)
    ]
    print(f"Fetching candidate documents: {len(strong_docs)}", flush=True)
    doc_text: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.workers, 32)) as executor:
        futures = {executor.submit(fetch_document, doc["url"], args.refresh): doc["url"] for doc in strong_docs}
        for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
            doc_text[futures[future]] = future.result()
            if n % 100 == 0:
                print(f"  documents {n}/{len(futures)}", flush=True)

    for logged in query_log:
        rows_for_title = title_to_rows[logged["title"]]
        for doc in strong_docs:
            body = doc_text.get(doc["url"], "")
            if not body:
                continue
            page = "<pre>" + html.escape(body) + "</pre>"
            found, seen, _ = scan_page(doc["url"], page, rows_for_title)
            for item in found:
                item["evidence_kind"] = "document"
            candidates.extend(found)
            title_seen.extend(seen)

    deduped_candidates = list({
        (row["paper_id"], row["candidate_status"], row["journal"], row["evidence_url"]): row
        for row in candidates
    }.values())
    deduped_seen = list({
        (row["paper_id"], row["evidence_url"]): row for row in title_seen
    }.values())

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(output.read_text()) if output.exists() else []
    merged = list({
        (row.get("paper_id"), row.get("candidate_status"), row.get("journal"), row.get("evidence_url")): row
        for row in [*existing, *deduped_candidates]
    }.values())
    output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")

    seen_output = output.with_name(output.stem.replace("_candidates", "_title_seen") + output.suffix)
    existing_seen = json.loads(seen_output.read_text()) if seen_output.exists() else []
    merged_seen = list({
        (row.get("paper_id"), row.get("evidence_url")): row
        for row in [*existing_seen, *deduped_seen]
    }.values())
    seen_output.write_text(json.dumps(merged_seen, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps({
        "lineages": len(lineages),
        "unique_pages": len(all_pages),
        "candidate_documents": len(strong_docs),
        "new_status_candidates": len(deduped_candidates),
        "merged_status_candidates": len(merged),
        "title_seen_without_status": len(deduped_seen),
        "output": str(output.relative_to(ROOT)),
    }, indent=2), flush=True)


if __name__ == "__main__":
    started = time.time()
    try:
        main()
    finally:
        print(f"elapsed_seconds={time.time() - started:.1f}", flush=True)
