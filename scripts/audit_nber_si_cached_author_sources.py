#!/usr/bin/env python3
"""Scan cached author pages/CVs for missed NBER SI publication/R&R statuses.

This script is intentionally cache-only: it does not fetch new pages. It is meant
to find review candidates among provisional NBER SI rows using author pages and
documents already discovered by ``audit_nber_si_cvs.py``.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_nber_si_cvs import (  # noqa: E402
    cache_path,
    direct_document_url,
    evidence_on_normalized,
    journal_near_status,
    match_norm,
    STATUS_RE,
    visible_text,
)
from nber_si_audit_common import author_surname, lineage_record, working_paper_lineages  # noqa: E402


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


def fuzzy_status_evidence(normalized: str, url: str, paper: dict,
                          source_author: str | None) -> list[dict]:
    """Generate conservative renamed-title R&R/acceptance candidates.

    The author source itself establishes one coauthor. For multi-author papers,
    every other conference coauthor surname must occur near the status phrase;
    the nearby text must also retain at least half of the agenda title's
    distinctive terms. These candidates never classify a paper automatically.
    """
    agenda_title = match_norm(paper["title"])
    title_terms = [
        token for token in agenda_title.split()
        if len(token) >= 5 and token not in {
            "about", "after", "among", "before", "between", "evidence", "effects",
            "using", "through", "their", "under", "with", "without", "paper",
        }
    ]
    source_surname = author_surname(source_author)
    all_surnames = {author_surname(name) for name in paper.get("authors_list") or []}
    required_surnames = {name for name in all_surnames if name and name != source_surname}
    results = []
    for hit in STATUS_RE.finditer(normalized):
        context_start = max(0, hit.start() - 500)
        context_end = min(len(normalized), hit.end() + 300)
        context = normalized[context_start:context_end]
        if required_surnames and not all(re.search(r"\b" + re.escape(name) + r"\b", context)
                                         for name in required_surnames):
            continue
        context_overlap = sorted({term for term in title_terms
                                  if re.search(r"\b" + re.escape(term) + r"\b", context)})
        context_coverage = len(context_overlap) / len(set(title_terms)) if title_terms else 0
        if len(context_overlap) < 2 or context_coverage < 0.7:
            continue
        term = hit.group(1).lower()
        status = "rr" if term in {
            "r r", "revise and resubmit", "revise resubmit", "major revision",
            "revision requested", "reject and resubmit", "reject resubmit",
        } else "published"
        local_before = normalized[max(0, hit.start() - 360):hit.start()]
        agenda_tokens = agenda_title.split()
        nearby_tokens = local_before.split()
        min_width = max(3, int(len(agenda_tokens) * 0.6))
        max_width = min(len(nearby_tokens), max(min_width, int(len(agenda_tokens) * 1.5)))
        ratio = 0.0
        best_end = 0
        best_text = ""
        for width in range(min_width, max_width + 1):
            for start in range(0, len(nearby_tokens) - width + 1):
                candidate_text = " ".join(nearby_tokens[start:start + width])
                candidate_ratio = difflib.SequenceMatcher(None, agenda_title, candidate_text).ratio()
                if candidate_ratio > ratio:
                    ratio = candidate_ratio
                    best_end = start + width
                    best_text = candidate_text
        tokens_between = len(nearby_tokens) - best_end
        overlap = sorted({term for term in title_terms
                          if re.search(r"\b" + re.escape(term) + r"\b", best_text)})
        coverage = len(overlap) / len(set(title_terms)) if title_terms else 0
        if (ratio < 0.65 or tokens_between > 15
                or len(overlap) < 2 or coverage < 0.7):
            continue
        status_window_start = max(0, hit.start() - 100)
        status_window = normalized[status_window_start:min(len(normalized), hit.end() + 160)]
        journal = journal_near_status(
            status_window,
            hit.start() - status_window_start,
            hit.end() - status_window_start,
        )
        if not journal:
            continue
        results.append({
            "paper_id": paper["id"],
            "title": paper["title"],
            "candidate_status": status,
            "journal": journal,
            "status_phrase": term,
            "evidence_url": url,
            "context": context,
            "distinctive_term_coverage": round(coverage, 3),
            "distinctive_term_overlap": overlap,
            "local_title_ratio": round(ratio, 3),
            "matched_title_text": best_text,
            "tokens_between_title_and_status": tokens_between,
            "author": source_author,
            "discovery": "same-coauthor fuzzy author-source lineage",
            "review_state": "needs_human_confirmation",
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--documents-per-author", type=int, default=0,
                        help="maximum documents per author; 0 scans every discovered document")
    parser.add_argument("--output", default="nber_si/data/cached_author_source_candidates.json")
    parser.add_argument("--attempts-output", default="nber_si/data/cached_author_source_attempts.json")
    args = parser.parse_args()

    data = ROOT / "nber_si" / "data"
    rows = json.loads((data / "papers_enriched.json").read_text())
    sources = json.loads((data / "cv_audit_sources.json").read_text())
    source_by_profile = {source.get("nber_profile"): source for source in sources
                         if source.get("nber_profile")}
    source_by_name = {}
    for source in sources:
        source_by_name.setdefault(match_norm(source.get("name") or ""), []).append(source)

    grouped = working_paper_lineages(rows)
    lineages = sorted(grouped.items(), key=lambda item: title_rank(item[1]))
    if args.offset:
        lineages = lineages[args.offset:]
    if args.limit:
        lineages = lineages[:args.limit]

    candidates = []
    attempts_output = ROOT / args.attempts_output
    existing_attempts = json.loads(attempts_output.read_text()) if attempts_output.exists() else {}
    attempts = {}
    seen = set()
    scanned = skipped = 0
    for n, (lineage_id, title_rows) in enumerate(lineages, 1):
        sibling_titles = [row["title"] for row in title_rows]
        lineage = lineage_record(lineage_id, title_rows)
        lineage_candidates_before = len(candidates)
        lineage_scanned = lineage_skipped = 0
        for profile in lineage.get("author_profiles") or []:
            author = profile.get("name")
            profile_url = profile.get("nber_url")
            if profile_url and profile_url.startswith("/"):
                profile_url = "https://www.nber.org" + profile_url
            source = source_by_profile.get(profile_url)
            if source is None:
                name_matches = source_by_name.get(match_norm(author or ""), [])
                source = max(name_matches, key=lambda item: (
                    bool(item.get("profile_fetch_ok")),
                    bool(item.get("external_pages")),
                    len(item.get("likely_documents") or []),
                )) if name_matches else {}
            sources_to_scan = [
                ("page", page["url"]) for page in source.get("external_pages", [])
            ]
            documents = source.get("likely_documents", [])
            if args.documents_per_author:
                documents = documents[:args.documents_per_author]
            sources_to_scan.extend(
                ("document", document["url"])
                for document in documents
            )
            for kind, url in sources_to_scan:
                page = cached_page(url, "document" if kind == "document" else "page")
                if page is None:
                    skipped += 1
                    lineage_skipped += 1
                    continue
                scanned += 1
                lineage_scanned += 1
                normalized_page = match_norm(page[5:-6] if kind == "document" and page.startswith("<pre>") else visible_text(page))
                for row in title_rows:
                    evidence = evidence_on_normalized(normalized_page, url, row, sibling_titles)
                    evidence_rows = [evidence] if evidence else fuzzy_status_evidence(
                        normalized_page, url, row, author
                    )
                    for evidence_row in evidence_rows:
                        if evidence_row is None:
                            continue
                        evidence_row["author"] = author
                        evidence_row["source_kind"] = kind
                        evidence_row["lineage_rank"] = args.offset + n
                        key = (
                            evidence_row["paper_id"],
                            evidence_row["candidate_status"],
                            evidence_row["journal"],
                            evidence_row["evidence_url"],
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        candidates.append(evidence_row)
        found = len(candidates) - lineage_candidates_before
        attempt_count = int(existing_attempts.get(lineage_id, {}).get("attempts") or 0) + 1
        attempts[lineage_id] = {
            "lineage_id": lineage_id,
            "title": lineage["title"],
            "state": (
                "candidate" if found
                else "no_hit" if lineage_scanned and not lineage_skipped
                else "exhausted_unavailable" if attempt_count >= 3
                else "pending"
            ),
            "attempts": attempt_count,
            "sources_scanned": lineage_scanned,
            "sources_missing_or_error": lineage_skipped,
            "candidates": found,
            "checked_at": "2026-07-14",
        }
        if n % 100 == 0:
            print(
                f"  scanned lineages {n}/{len(lineages)}; "
                f"sources {scanned}; candidates {len(candidates)}",
                flush=True,
            )

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(output.read_text()) if output.exists() else []
    # A full scan is authoritative for this derived candidate file. Tranche
    # runs still merge so offsets can be processed independently.
    if args.limit == 0 and args.offset == 0:
        existing = []
    # Fuzzy candidates are a derived slice: rebuild them under the current
    # conservative rule instead of preserving candidates from older thresholds.
    existing = [row for row in existing
                if row.get("discovery") != "same-coauthor fuzzy author-source lineage"]
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
    attempts_output.parent.mkdir(parents=True, exist_ok=True)
    existing_attempts.update(attempts)
    attempts_output.write_text(json.dumps(existing_attempts, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "lineages": len(lineages),
        "offset": args.offset,
        "cached_sources_scanned": scanned,
        "uncached_or_error_sources_skipped": skipped,
        "new_candidates_this_run": len(candidates),
        "merged_candidates": len(merged),
        "terminal_lineage_attempts": sum(row["state"] != "pending" for row in attempts.values()),
        "output": str(output.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
