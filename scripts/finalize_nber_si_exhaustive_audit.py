#!/usr/bin/env python3
"""Close candidate decisions and unresolved lineages only after every search pass.

This is the fixed-point guardrail. It cannot reject a weak candidate or label a
working paper exhaustively checked while any discovery or verification stage
for that lineage remains pending.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from audit_nber_si_cvs import match_norm
from build_nber_si_exhaustive_audit_state import candidate_key, materialize
from nber_si_audit_common import TERMINAL_STATES


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nber_si" / "data"
DECISIONS = DATA / "exhaustive_candidate_decisions.json"
CLOSEOUT = DATA / "exhaustive_unresolved_closeout.json"


def load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def main() -> None:
    audit = materialize()
    terminal_without_decisions = {}
    for lineage in audit["lineages"]:
        other_stages = {
            name: value for name, value in lineage["stages"].items()
            if name != "candidate_decisions"
        }
        terminal_without_decisions[lineage["lineage_id"]] = all(
            value["state"] in TERMINAL_STATES for value in other_stages.values()
        )

    decisions = load(DECISIONS, {})
    rows = load(DATA / "papers_enriched.json", [])
    by_id = {row["id"]: row for row in rows}
    candidates = [
        *load(DATA / "cv_audit_candidates.json", []),
        *load(DATA / "cached_author_source_candidates.json", []),
        *load(DATA / "provisional_web_audit_candidates.json", []),
        *load(DATA / "renamed_lineage_candidates.json", []),
    ]
    candidates_by_paper = {}
    for candidate in candidates:
        if candidate.get("paper_id"):
            candidates_by_paper.setdefault(candidate["paper_id"], []).append(candidate)

    rejected = 0
    for lineage in audit["lineages"]:
        if not terminal_without_decisions[lineage["lineage_id"]]:
            continue
        for paper_id in lineage["appearance_ids"]:
            if by_id.get(paper_id, {}).get("status") != "working_paper":
                continue
            for candidate in candidates_by_paper.get(paper_id, []):
                key = candidate_key(candidate)
                if key in decisions:
                    continue
                decisions[key] = {
                    "state": "rejected",
                    "reason": "all discovery passes completed; insufficient evidence to join this candidate to the agenda-paper lineage",
                    "paper_id": paper_id,
                    "doi": (candidate.get("doi") or "").lower(),
                    "reviewed_at": date.today().isoformat(),
                    "closeout": True,
                }
                rejected += 1
    DECISIONS.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + "\n")

    # Recompute after terminal candidate decisions. Only genuinely complete,
    # still-unresolved working-paper lineages receive the closeout label.
    closed_state = materialize()
    closeouts = []
    for lineage in closed_state["lineages"]:
        if not lineage["audit_complete"]:
            continue
        unresolved_ids = [
            paper_id for paper_id in lineage["appearance_ids"]
            if by_id.get(paper_id, {}).get("status") == "working_paper"
        ]
        if not unresolved_ids:
            continue
        closeouts.append({
            "lineage_id": lineage["lineage_id"],
            "normalized_title": match_norm(lineage["title"]),
            "appearance_ids": unresolved_ids,
            "reviewed_at": date.today().isoformat(),
            "verification": "exhaustively_checked_no_verified_status",
            "note": "Every applicable official-record, bibliographic, author-source, renamed-lineage, and web-discovery pass reached a terminal result without verified publication or named-journal R&R evidence.",
        })
    CLOSEOUT.write_text(json.dumps(closeouts, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "new_terminal_candidate_rejections": rejected,
        "exhaustively_checked_unresolved_lineages": len(closeouts),
        "exhaustively_checked_unresolved_appearances": sum(len(row["appearance_ids"]) for row in closeouts),
    }, indent=2))


if __name__ == "__main__":
    main()
