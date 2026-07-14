#!/usr/bin/env python3
"""Build a prioritized review queue for unresolved NBER SI papers."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_nber_si_cvs import match_norm  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def author_url_count(row: dict) -> int:
    return sum(1 for profile in row.get("author_profiles") or [] if profile.get("nber_url"))


def review_priority(rows: list[dict]) -> tuple:
    """Sort by likely value of another manual/web pass."""
    max_year = max(row["year"] for row in rows)
    appearances = len(rows)
    has_nber_wp = any(row.get("nber_working_paper") for row in rows)
    author_profiles = max(author_url_count(row) for row in rows)
    return (-max_year, -appearances, -int(has_nber_wp), -author_profiles, rows[0]["title"].casefold())


def suggested_queries(row: dict) -> list[str]:
    title = row["title"]
    authors = row.get("authors_list") or []
    queries = [
        f'"{title}"',
        f'"{title}" "revise and resubmit"',
        f'"{title}" "accepted"',
        f'"{title}" "forthcoming"',
    ]
    for author in authors[:3]:
        queries.append(f'"{title}" "{author}"')
    return queries


def main() -> None:
    data = ROOT / "nber_si" / "data"
    rows = json.loads((data / "papers_enriched.json").read_text())
    candidates_path = data / "provisional_web_audit_candidates.json"
    web_candidates = json.loads(candidates_path.read_text()) if candidates_path.exists() else []
    candidate_by_title = defaultdict(list)
    by_id = {row["id"]: row for row in rows}
    for candidate in web_candidates:
        paper = by_id.get(candidate.get("paper_id"))
        if paper:
            candidate_by_title[match_norm(paper["title"])].append(candidate)

    grouped = defaultdict(list)
    for row in rows:
        if row.get("status") == "working_paper" and row.get("verification") == "provisional":
            grouped[match_norm(row["title"])].append(row)

    output = data / "provisional_review_queue.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "rank", "title", "authors", "years", "programs", "appearances",
            "has_nber_wp", "paper_urls", "author_profile_count", "candidate_count",
            "candidate_journals", "suggested_queries",
        ])
        writer.writeheader()
        for rank, title_rows in enumerate(sorted(grouped.values(), key=review_priority), 1):
            first = title_rows[0]
            key = match_norm(first["title"])
            candidates = candidate_by_title.get(key, [])
            writer.writerow({
                "rank": rank,
                "title": first["title"],
                "authors": first.get("authors") or first.get("agenda_authors"),
                "years": "; ".join(str(year) for year in sorted({row["year"] for row in title_rows})),
                "programs": "; ".join(sorted({row["program"] for row in title_rows})),
                "appearances": len(title_rows),
                "has_nber_wp": any(row.get("nber_working_paper") for row in title_rows),
                "paper_urls": "; ".join(sorted({row.get("paper_url") or "" for row in title_rows if row.get("paper_url")})),
                "author_profile_count": max(author_url_count(row) for row in title_rows),
                "candidate_count": len(candidates),
                "candidate_journals": "; ".join(sorted({
                    re.sub(r"\s+", " ", candidate.get("journal") or "").strip()
                    for candidate in candidates if candidate.get("journal")
                })),
                "suggested_queries": " | ".join(suggested_queries(first)),
            })
    print(f"wrote {output.relative_to(ROOT)} ({len(grouped)} title lineages)")


if __name__ == "__main__":
    main()
