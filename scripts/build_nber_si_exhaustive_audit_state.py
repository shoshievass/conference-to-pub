#!/usr/bin/env python3
"""Materialize the fixed-point state of the exhaustive NBER SI audit.

The state distinguishes an unresolved classification from an incomplete audit.
It never treats a zero-result search or a cached fetch error as evidence that a
paper remains unpublished.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from audit_nber_si_cvs import cache_path, direct_document_url, match_norm
from audit_nber_si_renamed_lineages import crossref_cache_path, distinctive_terms
from enrich_nber_si import crossref_path, nber_wp_path
from nber_si_audit_common import TERMINAL_STATES, lineage_record, working_paper_lineages


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nber_si" / "data"
STATE_PATH = DATA / "exhaustive_audit_state.json"
ATTEMPTS_PATH = DATA / "exhaustive_audit_attempts.json"

STAGES = {
    "official_nber": "Refresh and inspect every applicable NBER working-paper Published Versions record.",
    "crossref_exact": "Search exact and normalized title/author journal metadata in Crossref.",
    "crossref_renamed": "Search post-conference same-author Crossref records for renamed projects.",
    "author_profiles": "Fetch every official NBER coauthor profile, retrying failures.",
    "author_web_discovery": "Discover a current homepage/research/CV source for every coauthor where possible.",
    "author_sources": "Fetch and scan every discovered current author page and strong document.",
    "author_exact_status": "Search author sources for exact-title named-journal R&R/acceptance/publication evidence.",
    "author_fuzzy_lineage": "Search author sources for renamed projects using title continuity and the full nearby coauthor set.",
    "broad_title_web": "Run exact-title, coauthor, and status-phrase web discovery queries.",
    "scholar_discovery": "Use Google Scholar as a discovery layer; snippets alone never determine status.",
    "renamed_candidate_verification": "Check every plausible renamed candidate with DOI/publisher metadata and first-page lineage evidence.",
    "candidate_decisions": "Give every generated status candidate a terminal accepted or rejected decision.",
}


def load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def usable_cache(path: Path) -> bool:
    return path.exists() and "FETCH_ERROR" not in path.read_text(errors="replace")


def stage(state: str, **details) -> dict:
    return {"state": state, **details}


def candidate_key(row: dict) -> str:
    raw = "|".join(str(row.get(key) or "") for key in (
        "paper_id", "candidate_status", "candidate_title", "journal", "doi", "evidence_url", "url"
    ))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def renamed_query_url(row: dict, author: str | None = None) -> str:
    """Reproduce the renamed-lineage cache key without issuing a request."""
    params = {
        "query.author": author or (row.get("authors_list") or [row.get("agenda_authors", "")])[0],
        "query.bibliographic": " ".join(distinctive_terms(row["title"])[:5]),
        "rows": "12",
        "filter": "type:journal-article",
        "select": "DOI,title,container-title,published,issued,published-print,published-online,author,URL,type",
    }
    return "https://api.crossref.org/works?" + urllib.parse.urlencode(params)


def materialize() -> dict:
    papers = load(DATA / "papers_enriched.json", [])
    lineages = working_paper_lineages(papers)
    attempts = load(ATTEMPTS_PATH, {"schema_version": 1, "lineages": {}, "candidates": {}})
    candidate_decisions = load(DATA / "exhaustive_candidate_decisions.json", {})
    sources = load(DATA / "cv_audit_sources.json", [])
    source_by_profile = {row.get("nber_profile"): row for row in sources if row.get("nber_profile")}
    sources_by_name = defaultdict(list)
    for source in sources:
        sources_by_name[match_norm(source.get("name") or "")].append(source)

    cv_candidates = load(DATA / "cv_audit_candidates.json", [])
    cached_candidates = load(DATA / "cached_author_source_candidates.json", [])
    web_candidates = load(DATA / "provisional_web_audit_candidates.json", [])
    renamed_candidates = load(DATA / "renamed_lineage_candidates.json", [])
    confirmed_renamed = {row.get("paper_id") for row in load(DATA / "renamed_lineage_confirmed.json", [])}
    rejected_cv = {
        match_norm(row if isinstance(row, str) else row.get("title") or row.get("normalized_title") or "")
        for row in load(DATA / "cv_audit_rejected_candidates.json", [])
    }
    scholar_rows = {
        match_norm(row.get("agenda_title") or ""): row
        for row in load(DATA / "scholar_audit_candidates.json", [])
    }
    scholar_provider = load(DATA / "scholar_provider_status.json", {})
    web_provider = load(DATA / "web_search_provider_status.json", {})
    no_status = {
        row.get("normalized_title") for row in load(DATA / "cv_no_status_checks.json", [])
    }
    web_attempts = load(DATA / "provisional_web_audit_attempts.json", {})
    openalex_attempts = load(DATA / "openalex_audit_candidates.json", {})
    cached_author_attempts = load(DATA / "cached_author_source_attempts.json", {})
    renamed_crossref_attempts = load(DATA / "renamed_crossref_attempts.json", {})

    candidates_by_paper = defaultdict(list)
    for candidate in [*cv_candidates, *cached_candidates, *web_candidates, *renamed_candidates]:
        if candidate.get("paper_id"):
            candidates_by_paper[candidate["paper_id"]].append(candidate)

    records = []
    for lineage_id, rows in sorted(lineages.items()):
        record = lineage_record(lineage_id, rows)
        title_key = record["normalized_title"]
        paper_ids = set(record["appearance_ids"])
        prior = attempts.get("lineages", {}).get(lineage_id, {})
        stages = {}

        nber_numbers = record["nber_working_papers"]
        if not nber_numbers:
            stages["official_nber"] = stage("not_applicable")
        else:
            paths = [nber_wp_path(number) for number in nber_numbers]
            ok = [usable_cache(path) for path in paths]
            stages["official_nber"] = stage(
                "no_hit" if all(ok) else "pending",
                records=len(paths), successful=sum(ok),
            )

        exact_paths = [crossref_path(row["title"]) for row in rows]
        exact_ok = [path.exists() and '"error"' not in path.read_text(errors="replace") for path in exact_paths]
        stages["crossref_exact"] = stage(
            "no_hit" if all(exact_ok) else "pending",
            queries=len(exact_paths), successful=sum(exact_ok),
        )

        renamed_paths = []
        renamed_row = min(rows, key=lambda row: (
            row.get("year") or 9999, row.get("program") or "", row.get("title") or ""
        ))
        query_authors = renamed_row.get("authors_list") or [None]
        renamed_paths.extend(
            crossref_cache_path(renamed_query_url(renamed_row, author))
            for author in query_authors[:3]
        )
        renamed_ok = bool(renamed_paths) and all(path.exists() for path in renamed_paths)
        lineage_renamed = [c for pid in paper_ids for c in candidates_by_paper.get(pid, [])
                           if c.get("candidate_title")]
        renamed_attempt = renamed_crossref_attempts.get(lineage_id, {})
        renamed_state = (
            "candidate" if lineage_renamed
            else "no_hit" if renamed_ok
            else renamed_attempt.get("state", "pending")
        )
        stages["crossref_renamed"] = stage(
            renamed_state,
            candidates=len(lineage_renamed), queries=len(renamed_paths),
        )

        author_sources = []
        for profile in record["author_profiles"]:
            url = profile.get("nber_url")
            if url and url.startswith("/"):
                url = "https://www.nber.org" + url
            source = source_by_profile.get(url)
            if not source:
                matches = sources_by_name.get(match_norm(profile.get("name") or ""), [])
                source = max(matches, key=lambda item: (
                    bool(item.get("profile_fetch_ok")),
                    bool(item.get("external_pages")),
                    len(item.get("likely_documents") or []),
                )) if matches else None
            author_sources.append((profile, source))
        profile_done = [bool(source and (
            source.get("profile_fetch_ok")
            or source.get("profile_fetch_state") in TERMINAL_STATES
        )) for _, source in author_sources]
        stages["author_profiles"] = stage(
            "complete" if profile_done and all(profile_done) else "pending",
            authors=len(author_sources), successful=sum(profile_done),
        )

        discovered = [source for _, source in author_sources if source and source.get("external_pages")]
        web_searched = [
            source for _, source in author_sources
            if source and (
                source.get("web_search_state") in TERMINAL_STATES
                or ("web_search_pages" in source and not source.get("web_search_state"))
            )
        ]
        provider_web_terminal = web_provider.get("state") in TERMINAL_STATES
        attempted_web_authors = len(author_sources) if provider_web_terminal else len(web_searched)
        stages["author_web_discovery"] = stage(
            ("exhausted_unavailable" if provider_web_terminal and len(web_searched) < len(author_sources)
             else "complete" if author_sources and len(web_searched) == len(author_sources)
             else "pending"),
            authors=len(author_sources), attempted=attempted_web_authors, with_source=len(discovered),
            provider_state=web_provider.get("state"),
        )

        pages, docs, good_pages, good_docs, failed_sources = 0, 0, 0, 0, 0
        for _, source in author_sources:
            if not source:
                continue
            for page in source.get("external_pages") or []:
                pages += 1
                if usable_cache(cache_path("external_pages", page["url"])):
                    good_pages += 1
                else:
                    failed_sources += 1
            for document in source.get("likely_documents") or []:
                docs += 1
                path = cache_path("document_text", direct_document_url(document["url"]), ".txt")
                if usable_cache(path):
                    good_docs += 1
                else:
                    failed_sources += 1
        if not pages and not docs and stages["author_web_discovery"]["state"] == "complete":
            source_state = "exhausted_unavailable"
        elif pages + docs and failed_sources == 0:
            source_state = "complete"
        else:
            source_state = "pending"
        cached_attempt = cached_author_attempts.get(lineage_id, {})
        if source_state == "pending" and (
            cached_attempt.get("state") == "exhausted_unavailable"
            or int(cached_attempt.get("attempts") or 0) >= 3
        ):
            source_state = "exhausted_unavailable"
        stages["author_sources"] = stage(
            source_state, pages=pages, pages_fetched=good_pages, documents=docs,
            documents_fetched=good_docs, failures=failed_sources,
        )

        author_candidates = [c for pid in paper_ids for c in candidates_by_paper.get(pid, [])
                             if c.get("candidate_status")]
        if author_candidates:
            author_exact_state = "candidate"
        elif title_key in no_status:
            author_exact_state = "no_hit"
        elif cached_attempt.get("state") in {"no_hit", "exhausted_unavailable"}:
            author_exact_state = "no_hit"
        elif source_state in {"complete", "exhausted_unavailable"}:
            author_exact_state = "no_hit"
        else:
            author_exact_state = "pending"
        stages["author_exact_status"] = stage(author_exact_state, candidates=len(author_candidates))
        fuzzy_candidates = [candidate for candidate in author_candidates
                            if candidate.get("discovery") == "same-coauthor fuzzy author-source lineage"]
        if fuzzy_candidates:
            fuzzy_state = "candidate"
        elif cached_attempt.get("state") in {"no_hit", "exhausted_unavailable", "candidate"}:
            fuzzy_state = "no_hit"
        else:
            fuzzy_state = "pending"
        stages["author_fuzzy_lineage"] = stage(fuzzy_state, candidates=len(fuzzy_candidates))

        web = web_attempts.get(lineage_id) or prior.get("broad_title_web") or {}
        broad_web_state = web.get("state", "pending")
        if broad_web_state not in TERMINAL_STATES and web_provider.get("state") in TERMINAL_STATES:
            broad_web_state = web_provider["state"]
        stages["broad_title_web"] = stage(
            broad_web_state,
            attempts=web.get("attempts", 0), queries=web.get("queries", 0),
            results=web.get("results", 0), error=web.get("error"),
            provider_state=web_provider.get("state"),
        )

        scholar = scholar_rows.get(title_key)
        if scholar and scholar.get("error"):
            scholar_state = scholar_provider.get("state", "pending")
        elif scholar:
            scholar_state = "candidate" if scholar.get("results") else "no_hit"
        else:
            scholar_state = scholar_provider.get("state") or prior.get("scholar_discovery", {}).get("state", "pending")
        stages["scholar_discovery"] = stage(
            scholar_state, results=len((scholar or {}).get("results") or []),
            error=(scholar or {}).get("error"),
        )

        openalex = openalex_attempts.get(lineage_id) or prior.get("openalex") or {}
        renamed_required = bool(lineage_renamed)
        if not renamed_required:
            renamed_verification_state = "not_applicable"
        else:
            renamed_verification_state = openalex.get("state", "pending")
        stages["renamed_candidate_verification"] = stage(
            renamed_verification_state,
            candidates=len(lineage_renamed),
            checked=openalex.get("checked", 0),
            pdf_checked=openalex.get("pdf_checked", 0),
        )

        decisions = candidate_decisions
        undecided = []
        for candidate in [*author_candidates, *lineage_renamed]:
            key = candidate_key(candidate)
            accepted = candidate.get("paper_id") in confirmed_renamed
            rejected = title_key in rejected_cv or decisions.get(key, {}).get("state") == "rejected"
            if not accepted and not rejected and decisions.get(key, {}).get("state") != "accepted":
                undecided.append(key)
        stages["candidate_decisions"] = stage(
            "complete" if not undecided else "pending",
            discovered=len(author_candidates) + len(lineage_renamed), undecided=len(set(undecided)),
        )

        incomplete = [name for name, value in stages.items() if value["state"] not in TERMINAL_STATES]
        record["stages"] = stages
        record["audit_complete"] = not incomplete
        record["incomplete_stages"] = incomplete
        records.append(record)

    stage_counts = {
        name: dict(Counter(record["stages"][name]["state"] for record in records))
        for name in STAGES
    }
    summary = {
        "working_paper_appearances": sum(len(record["appearance_ids"]) for record in records),
        "working_paper_lineages": len(records),
        "audit_complete_lineages": sum(record["audit_complete"] for record in records),
        "audit_incomplete_lineages": sum(not record["audit_complete"] for record in records),
        "stage_counts": stage_counts,
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": "2026-07-14",
        "required_stages": STAGES,
        "summary": summary,
        "lineages": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if any lineage has an incomplete required stage")
    args = parser.parse_args()
    state = materialize()
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(state["summary"], indent=2))
    if args.check and state["summary"]["audit_incomplete_lineages"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
