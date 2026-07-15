#!/usr/bin/env python3
"""Run the NBER SI audit to a documented fixed point.

The coordinator is intentionally conservative: discovery passes create
evidence and candidate decisions, while only curated decision applicators can
change publication status. It resumes from caches and stable lineage IDs, so a
classification change cannot shift offsets and silently skip later papers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "nber_si" / "data" / "exhaustive_audit_state.json"


def run(*args: str) -> None:
    command = [sys.executable, *args]
    print("RUN", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def state() -> dict:
    run("scripts/build_nber_si_exhaustive_audit_state.py")
    return json.loads(STATE.read_text())


def pending(summary: dict, stage_name: str) -> int:
    return int(summary["stage_counts"].get(stage_name, {}).get("pending", 0))


def local_cycle() -> dict:
    run("scripts/apply_nber_si_cv_audit.py")
    run("scripts/apply_nber_si_fuzzy_author_decisions.py")
    run("scripts/apply_nber_si_exhaustive_decisions.py")
    run("scripts/enrich_nber_si.py")
    run("scripts/audit_nber_si_cached_author_sources.py", "--limit", "0", "--documents-per-author", "0")
    run("scripts/build_nber_si_provisional_review_queue.py")
    current = state()
    run("scripts/finalize_nber_si_exhaustive_audit.py")
    run("scripts/enrich_nber_si.py")
    run("scripts/build_nber_si_provisional_review_queue.py")
    return state()


def network_cycle(current: dict, web_tranche: int, scholar_tranche: int,
                  renamed_authors: int, include_pdf: bool) -> None:
    summary = current["summary"]
    if pending(summary, "crossref_exact"):
        run("scripts/enrich_nber_si.py", "--lookup")
    if (pending(summary, "author_profiles") or pending(summary, "author_web_discovery")
            or pending(summary, "author_sources")):
        if pending(summary, "author_profiles"):
            run("scripts/audit_nber_si_cvs.py", "--reuse-sources")
        if pending(summary, "author_web_discovery"):
            run(
                "scripts/audit_nber_si_cvs.py", "--reuse-sources", "--skip-profile-retries",
                "--web-search", "--web-search-all", "--web-search-only-unattempted",
                "--web-search-limit", str(web_tranche), "--web-search-workers", "8",
            )
        if pending(summary, "author_sources"):
            run("scripts/audit_nber_si_cvs.py", "--reuse-sources", "--skip-profile-retries",
                "--external", "--documents")
    if pending(summary, "crossref_renamed"):
        command = [
            "scripts/audit_nber_si_renamed_lineages.py", "--limit", "0",
            "--max-authors", str(renamed_authors), "--pdf", "0" if include_pdf else "40",
        ]
        run(*command)
    if pending(summary, "renamed_candidate_verification"):
        command = ["scripts/audit_nber_si_openalex.py"]
        if include_pdf:
            command.append("--pdf")
        run(*command)
    if pending(summary, "broad_title_web"):
        run(
            "scripts/audit_nber_si_provisional_web.py", "--only-unattempted",
            "--limit", str(web_tranche), "--status-queries", "--max-authors", "0",
        )
    if pending(summary, "scholar_discovery"):
        run(
            "scripts/audit_nber_si_scholar.py", "--limit", str(scholar_tranche),
            "--retry-errors",
        )
    run("scripts/assess_nber_si_search_provider.py")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true", help="run external discovery passes")
    parser.add_argument("--max-cycles", type=int, default=1,
                        help="cycles to run; 0 continues until the fixed-point rule is satisfied")
    parser.add_argument("--web-tranche", type=int, default=100)
    parser.add_argument("--scholar-tranche", type=int, default=25)
    parser.add_argument("--renamed-authors", type=int, default=3)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()

    previous_signature = None
    stable_cycles = 0
    cycle = 0
    while args.max_cycles == 0 or cycle < args.max_cycles:
        cycle += 1
        print(f"\nAUDIT CYCLE {cycle}", flush=True)
        current = local_cycle()
        summary = current["summary"]
        signature = json.dumps(summary, sort_keys=True)
        stable_cycles = stable_cycles + 1 if signature == previous_signature else 0
        previous_signature = signature

        if summary["audit_incomplete_lineages"] == 0:
            # Require a second reconciliation cycle that creates no new work.
            if stable_cycles >= 1:
                print("FIXED POINT: every applicable pass and candidate decision is terminal", flush=True)
                break
            # A clean first cycle still needs one cache-only reconciliation;
            # it does not require network authority because all external stages
            # already have terminal success or provider-exhaustion records.
            continue
        if not args.network:
            print("STOPPED AFTER LOCAL CYCLE: external stages remain queued", flush=True)
            break
        network_cycle(current, args.web_tranche, args.scholar_tranche,
                      args.renamed_authors, args.pdf)
    else:
        print("CYCLE LIMIT REACHED: rerun to resume from the persisted ledger", flush=True)

    run("scripts/build_nber_si_dashboard.py")
    run("scripts/build_nber_si_exhaustive_audit_state.py")


if __name__ == "__main__":
    main()
