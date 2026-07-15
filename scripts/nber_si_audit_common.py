#!/usr/bin/env python3
"""Shared lineage helpers for the exhaustive NBER SI status audit."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from audit_nber_si_cvs import match_norm


TERMINAL_STATES = {
    "complete",
    "no_hit",
    "candidate",
    "not_applicable",
    "exhausted_unavailable",
}


def author_key(name: str | None) -> str:
    """Normalize an agenda author for stable lineage identity."""
    return match_norm(name or "")


def author_surname(name: str | None) -> str:
    tokens = author_key(name).split()
    return tokens[-1] if tokens else ""


def row_author_keys(row: dict) -> tuple[str, ...]:
    names = row.get("authors_list") or []
    if not names and row.get("agenda_authors"):
        names = re.split(r"\s*(?:,|;|\band\b)\s*", row["agenda_authors"])
    return tuple(sorted({key for name in names if (key := author_key(name))}))


def lineage_id_for_row(row: dict) -> str:
    """Use title plus full author set so unrelated same-title papers never merge."""
    payload = match_norm(row.get("title") or "") + "|" + "|".join(row_author_keys(row))
    return "nbersi-lineage-" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def working_paper_lineages(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("status") == "working_paper":
            grouped[lineage_id_for_row(row)].append(row)
    return dict(grouped)


def lineage_record(lineage_id: str, rows: list[dict]) -> dict:
    first = min(rows, key=lambda row: (row.get("year") or 9999, row.get("id") or ""))
    authors = sorted({name for row in rows for name in (row.get("authors_list") or [])})
    profiles = {}
    for row in rows:
        for profile in row.get("author_profiles") or []:
            key = profile.get("nber_url") or author_key(profile.get("name"))
            if key:
                profiles[key] = profile
    return {
        "lineage_id": lineage_id,
        "title": first["title"],
        "normalized_title": match_norm(first["title"]),
        "authors": authors,
        "author_keys": list(row_author_keys(first)),
        "author_profiles": sorted(profiles.values(), key=lambda item: (
            author_key(item.get("name")), item.get("nber_url") or ""
        )),
        "appearance_ids": sorted(row["id"] for row in rows),
        "years": sorted({row["year"] for row in rows}),
        "programs": sorted({row["program"] for row in rows}),
        "nber_working_papers": sorted({
            row["nber_working_paper"] for row in rows if row.get("nber_working_paper")
        }),
        "paper_urls": sorted({row["paper_url"] for row in rows if row.get("paper_url")}),
        "verification_levels": sorted({row.get("verification") or "" for row in rows}),
    }
