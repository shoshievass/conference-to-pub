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
from nber_si_audit_common import lineage_record, working_paper_lineages  # noqa: E402


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

    grouped = working_paper_lineages(rows)
    audit_state_path = data / "exhaustive_audit_state.json"
    audit_state = json.loads(audit_state_path.read_text()) if audit_state_path.exists() else {"lineages": []}
    audit_by_id = {row["lineage_id"]: row for row in audit_state.get("lineages", [])}

    output = data / "provisional_review_queue.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, lineterminator="\n", fieldnames=[
            "rank", "lineage_id", "title", "authors", "years", "programs", "appearances",
            "has_nber_wp", "paper_urls", "author_profile_count", "candidate_count",
            "candidate_journals", "audit_complete", "incomplete_stages", "suggested_queries",
        ])
        writer.writeheader()
        ordered = sorted(grouped.items(), key=lambda item: review_priority(item[1]))
        for rank, (lineage_id, title_rows) in enumerate(ordered, 1):
            first = title_rows[0]
            key = match_norm(first["title"])
            candidates = candidate_by_title.get(key, [])
            audit = audit_by_id.get(lineage_id, {})
            writer.writerow({
                "rank": rank,
                "lineage_id": lineage_id,
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
                "audit_complete": audit.get("audit_complete", False),
                "incomplete_stages": "; ".join(audit.get("incomplete_stages") or []),
                "suggested_queries": " | ".join(suggested_queries(first)),
            })
    print(f"wrote {output.relative_to(ROOT)} ({len(grouped)} stable working-paper lineages)")


if __name__ == "__main__":
    main()
