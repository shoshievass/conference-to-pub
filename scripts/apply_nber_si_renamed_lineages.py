#!/usr/bin/env python3
"""Promote conservative renamed-lineage candidates into the curated audit file."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "nber_si" / "data" / "renamed_lineage_candidates.json"
CONFIRMED = ROOT / "nber_si" / "data" / "renamed_lineage_confirmed.json"


def clean_title(title: str) -> str:
    title = re.sub(r"<[^>]+>", "", title or "")
    return re.sub(r"\*+$", "", title).strip()


def promotable(row: dict) -> bool:
    candidate_title = row["candidate_title"].casefold()
    if any(term in candidate_title for term in ("corrigendum", "reply", "comment")):
        return False
    if row.get("journal", "").casefold() == "isee conference abstracts":
        return False
    overlap = row.get("distinctive_term_overlap") or []
    ratio = row["title_ratio"]
    coverage = row["distinctive_term_coverage"]
    if len(overlap) < 3 and not (coverage >= 1.0 and ratio >= 0.60 and len(overlap) >= 1):
        return False
    old_strict = ratio >= 0.75 and coverage >= 0.75
    gautreaux_style = ratio >= 0.82 and coverage >= 0.625
    short_title_with_subtitle = coverage >= 1.0 and ratio >= 0.60
    retitled_with_high_overlap = coverage >= 0.875 and ratio >= 0.70
    retitled_with_strong_overlap = coverage >= 0.75 and ratio >= 0.70
    return (
        old_strict
        or gautreaux_style
        or short_title_with_subtitle
        or retitled_with_high_overlap
        or retitled_with_strong_overlap
    )


def note(row: dict) -> str:
    overlap = ", ".join(row.get("distinctive_term_overlap") or [])
    return (
        "Same author set and post-conference journal record; "
        f"agenda/published title fuzzy score {row['title_ratio']:.3f}, "
        f"distinctive-term coverage {row['distinctive_term_coverage']:.3f}"
        f" ({overlap}). Cross-checked by renamed-lineage audit in July 2026."
    )


def main() -> None:
    candidates = json.loads(CANDIDATES.read_text())
    confirmed = json.loads(CONFIRMED.read_text())
    by_paper = {row["paper_id"]: row for row in confirmed}
    added = []
    for row in candidates:
        if row["paper_id"] in by_paper or not promotable(row):
            continue
        candidate = {
            "paper_id": row["paper_id"],
            "normalized_title": re.sub(r"[^a-z0-9]+", " ", row["agenda_title"].lower()).strip(),
            "title": row["agenda_title"],
            "status": "published",
            "journal": row["journal"],
            "pub_year": row["candidate_year"],
            "published_title": clean_title(row["candidate_title"]),
            "url": row["url"],
            "evidence_url": row["url"],
            "reviewed_at": "2026-07-14",
            "evidence_source": (
                "same-author renamed-lineage audit: Crossref author-keyword candidate, "
                "fuzzy title/project match, post-conference journal record"
            ),
            "note": note(row),
        }
        by_paper[row["paper_id"]] = candidate
        added.append(candidate)
    CONFIRMED.write_text(json.dumps(confirmed + added, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "candidate_lineages": len(candidates),
        "added_confirmed_lineages": len(added),
        "total_confirmed_lineages": len(confirmed) + len(added),
    }, indent=2))


if __name__ == "__main__":
    main()
