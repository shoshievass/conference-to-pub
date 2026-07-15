#!/usr/bin/env python3
"""Apply conservative decisions for same-coauthor fuzzy author-source matches."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from audit_nber_si_cvs import match_norm
from build_nber_si_exhaustive_audit_state import candidate_key


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nber_si" / "data"


def distinct_evidence(rows: list[dict]) -> list[dict]:
    by_author = {}
    for row in rows:
        author = row.get("author") or "coauthor source"
        by_author.setdefault(author, {
            "author": author,
            "evidence_url": row["evidence_url"],
            "status_phrase": row.get("status_phrase") or "verified status",
        })
    return list(by_author.values())


def metrics(rows: list[dict]) -> dict:
    exact = any(row.get("discovery") != "same-coauthor fuzzy author-source lineage" for row in rows)
    return {
        "authors": len(distinct_evidence(rows)),
        "exact_title": exact,
        "min_between": min(int(row.get("tokens_between_title_and_status") if row.get("tokens_between_title_and_status") is not None else 999) for row in rows),
        "max_ratio": max(float(row.get("local_title_ratio") or (1.0 if exact else 0)) for row in rows),
        "max_coverage": max(float(row.get("distinctive_term_coverage") or (1.0 if exact else 0)) for row in rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    papers = {row["id"]: row for row in json.loads((DATA / "papers_enriched.json").read_text())}
    all_candidates = json.loads((DATA / "cached_author_source_candidates.json").read_text())
    candidate_rows = all_candidates
    rejected_titles = {
        match_norm(row.get("title") or row.get("normalized_title") or "")
        for row in json.loads((DATA / "cv_audit_rejected_candidates.json").read_text())
    }
    # Exact-title extraction can still cross a page/CV entry boundary when the
    # next paper carries the nearby status. These cases were checked against the
    # live author pages and drafts on 2026-07-14 and are explicit negatives.
    rejected_titles.update(match_norm(title) for title in {
        "American Life Histories",
        "Asset Purchase Rules: How QE Transformed the Bond Market",
        "Breaking Parity: Equilibrium Exchange Rates and Currency Premia",
        "How Disability Benefits in Early Life Affect Adult Outcomes",
        "How Do Neighborhoods and Firms Affect Intergenerational Mobility?",
        "How Much Should We Spend to Reduce A.I.'s Existential Risk?",
        "Quality in the Generic Drug Market",
        "Redistribution in Environmental Permit Markets: Transfers and Efficiency Costs with Trade Restrictions",
        "The Labor Market as an Equilibrium Newsvendor Problem",
    })
    option_rows = defaultdict(list)
    for row in candidate_rows:
        option_rows[(row["paper_id"], row["candidate_status"], row["journal"])].append(row)

    options_by_paper = defaultdict(list)
    for identity, rows in option_rows.items():
        option = {"identity": identity, "rows": rows, **metrics(rows)}
        options_by_paper[identity[0]].append(option)

    chosen = {}
    for paper_id, options in options_by_paper.items():
        best = min(options, key=lambda option: (
            option["min_between"],
            -option["authors"],
            -(option["identity"][1] == "published"),
            -option["max_ratio"],
            -option["max_coverage"],
        ))
        qualified = (
            best["min_between"] <= 15
            and best["max_coverage"] >= 0.7
            and (
                best["max_ratio"] >= 0.75
                or (best["authors"] >= 2 and best["max_ratio"] >= 0.65)
            )
        )
        if qualified and match_norm(papers.get(paper_id, {}).get("title") or "") not in rejected_titles:
            chosen[paper_id] = best

    summary = {
        "cached_author_candidate_rows": len(candidate_rows),
        "candidate_papers": len(options_by_paper),
        "accepted_papers": len(chosen),
        "multiple_author_accepts": sum(option["authors"] >= 2 for option in chosen.values()),
        "single_author_high_proximity_accepts": sum(option["authors"] == 1 for option in chosen.values()),
        "rejected_or_insufficient_papers": len(options_by_paper) - len(chosen),
    }
    if args.dry_run:
        summary["accepted"] = [
            {
                "paper_id": paper_id,
                "title": papers.get(paper_id, {}).get("title"),
                "status": option["identity"][1],
                "journal": option["identity"][2],
                "authors": option["authors"],
                "min_between": option["min_between"],
                "title_ratio": option["max_ratio"],
                "coverage": option["max_coverage"],
            }
            for paper_id, option in sorted(chosen.items())
        ]
        print(json.dumps(summary, indent=2))
        return

    audit_path = DATA / "cv_audit.json"
    audit_rows = json.loads(audit_path.read_text()) if audit_path.exists() else []
    audit = {match_norm(row.get("title") or row.get("normalized_title") or ""): row
             for row in audit_rows}
    decisions_path = DATA / "exhaustive_candidate_decisions.json"
    decisions = json.loads(decisions_path.read_text()) if decisions_path.exists() else {}
    decision_manifest = []

    for paper_id, options in options_by_paper.items():
        selected = chosen.get(paper_id)
        selected_identity = selected["identity"] if selected else None
        paper = papers.get(paper_id)
        for option in options:
            accepted = option["identity"] == selected_identity
            for row in option["rows"]:
                decisions[candidate_key(row)] = {
                    "state": "accepted" if accepted else "rejected",
                    "reason": (
                        "same-coauthor fuzzy author-source review confirmed a high-proximity named-journal status"
                        if accepted else
                        "same-coauthor fuzzy author-source review found lower-proximity, conflicting, or insufficient lineage evidence"
                    ),
                    "paper_id": paper_id,
                    "doi": "",
                    "reviewed_at": "2026-07-14",
                }
        if not selected or not paper or paper.get("status") != "working_paper":
            continue
        status = selected_identity[1]
        journal = selected_identity[2]
        evidence = distinct_evidence(selected["rows"])
        title_key = match_norm(paper["title"])
        record = {
            "normalized_title": title_key,
            "title": paper["title"],
            "status": status,
            "journal": journal,
            "pub_year": None,
            "evidence_url": evidence[0]["evidence_url"],
            "evidence_author": evidence[0]["author"],
            "evidence_phrase": evidence[0]["status_phrase"],
            "evidence": evidence,
            "reviewed_at": "2026-07-14",
            "review_method": "same-coauthor fuzzy author-source fixed-point review",
        }
        # Preserve an already curated exact-title or multi-author decision.
        audit.setdefault(title_key, record)
        decision_manifest.append({
            "paper_id": paper_id,
            "title": paper["title"],
            "status": status,
            "journal": journal,
            "authors_cross_checked": [row["author"] for row in evidence],
            "min_tokens_between_title_and_status": selected["min_between"],
            "max_title_ratio": selected["max_ratio"],
            "max_distinctive_term_coverage": selected["max_coverage"],
        })

    audit_path.write_text(json.dumps(list(audit.values()), indent=2, ensure_ascii=False) + "\n")
    decisions_path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + "\n")
    manifest_path = DATA / "fuzzy_author_source_decisions.json"
    prior_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    manifest_by_title = {match_norm(row.get("title") or ""): row for row in prior_manifest}
    for row in decision_manifest:
        manifest_by_title[match_norm(row.get("title") or "")] = row
    # Reconstruct durable history from the audit ledger if an earlier run of
    # this script predated manifest preservation. Resolved papers leave the
    # working-paper candidate queue, but their accepted decision must remain
    # auditable on every subsequent fixed-point cycle.
    for row in audit.values():
        if row.get("review_method") != "same-coauthor fuzzy author-source fixed-point review":
            continue
        title_key = match_norm(row.get("title") or "")
        manifest_by_title.setdefault(title_key, {
            "paper_id": "",
            "title": row.get("title"),
            "status": row.get("status"),
            "journal": row.get("journal"),
            "authors_cross_checked": [
                evidence.get("author") for evidence in row.get("evidence") or []
                if evidence.get("author")
            ],
            "min_tokens_between_title_and_status": None,
            "max_title_ratio": None,
            "max_distinctive_term_coverage": None,
        })
    manifest_path.write_text(
        json.dumps(sorted(manifest_by_title.values(), key=lambda row: (row.get("title") or "").casefold()),
                   indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
