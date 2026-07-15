# NBER Summer Institute program dashboard

This dashboard follows papers presented across NBER Summer Institute programs and workshops from
2015 through 2026. It is separate from the project's IO-conference dashboard. The current status
snapshot was pulled and cross-checked on **July 14, 2026**.

The versioned dataset contains **6,990 paper appearances**: 3,161 published/accepted/forthcoming,
328 named-journal R&Rs, and 3,501 working-paper appearances. A repeated paper contributes one
appearance to each program-year in which it was presented.

## Agenda collection

`scripts/collect_nber_si.py` starts from each official annual NBER Summer Institute schedule,
discovers every linked meeting, reads the meeting's public NBER conference API, and retains agenda
items with an actual paper record. Breaks, meals, panels, welcomes, and lectures without a paper
record are excluded. The collector preserves the official meeting title and date, authors, paper
link, NBER working-paper number when present, and source URL.

Obvious recurring program names are joined into stable series (for example, **Children** with
**Children and Families**, and the IT/digitization sequence with **Digital Economics and Artificial
Intelligence**). Related but distinct workshops are not silently merged. Both the canonical program
and the official meeting title remain in the downloadable data.

## Status definitions

The dashboard uses exactly three outcomes:

- **Published** includes published, accepted, conditionally accepted, and forthcoming journal articles.
- **R&R** requires a named-journal revise-and-resubmit, reject-and-resubmit, major revision, or revision requested.
- **Working paper** means that no publication, acceptance, or named-journal R&R was verified by the completed audit.

“Working paper” is an unresolved classification, not proof that a paper has never received an
editorial decision. Generic phrases such as “under review” do not qualify as an R&R. NBER, CEPR,
SSRN, and other working-paper series do not count as journal publications.

## Recursive publication audit

`scripts/run_nber_si_exhaustive_audit.py` runs a resumable fixed-point audit. Lineages use a stable
hash of normalized agenda title plus the full author set, so removing newly classified papers from
the working-paper queue cannot shift an offset and skip later papers. Each cycle rebuilds the queue,
applies reviewed decisions, rescans every cached author source, and materializes an audit ledger.
Completion requires all stages to be terminal and then a second complete reconciliation cycle that
creates no new accepted evidence.

Every unresolved working-paper lineage passes through these stages:

1. official NBER **Published Versions** metadata;
2. exact-title and normalized-title Crossref journal metadata;
3. post-conference same-author Crossref searches for renamed projects;
4. every available official NBER coauthor profile;
5. homepage, research-page, and CV discovery for each coauthor;
6. every cached discovered author page and strong document;
7. exact-title named-journal status extraction;
8. fuzzy renamed-title extraction requiring distinctive title continuity and the nearby coauthor set;
9. broad exact-title/coauthor/status web discovery;
10. Google Scholar discovery (never accepted from a snippet alone);
11. DOI/publisher/OpenAlex and first-page PDF review for plausible renamed candidates; and
12. a terminal accepted or rejected decision for every generated candidate.

The July 14 fixed point covers **3,155 working-paper lineages / 3,501 appearances**. All 3,155 have
all 12 applicable stages terminal; **zero provisional or audit-incomplete lineages remain**. The
second reconciliation cycle accepted zero additional candidates.

Terminal does not always mean a successful request. Google Scholar returned a traffic/CAPTCHA page,
so its remaining queue is recorded as provider-exhausted. DuckDuckGo Lite failed a 1,517-row probe
after at least 5,526 combined discovery queries, so the remaining broad-title and missing-homepage
queues are likewise recorded as provider-exhausted rather than as successful “no hit” searches.
Three individual renamed-title Crossref requests failed after three bounded retries each; their other
two coauthor queries and every other audit stage completed, and those failures are explicitly stored
as `exhausted_unavailable`.

The final state is in `data/exhaustive_audit_state.json`; terminal candidate decisions are in
`data/exhaustive_candidate_decisions.json`; unresolved closeout records are in
`data/exhaustive_unresolved_closeout.json`. Provider and retry ledgers make unavailable searches
distinguishable from successful zero-result searches.

## Author-source and renamed-title matching

The audit ledger contains 6,386 author-source records: 4,033 completed official-profile fetches,
1,736 exhausted profile failures, and 12 authors for whom an official profile was not applicable.
It discovered 1,780 unique external pages and 9,030 linked candidate documents. The cache-only final
scan inspected 24,655 lineage/source combinations; 1,707 uncached or failed sources were retained as
explicitly unavailable rather than silently counted as checks.

Exact-title evidence must place the named journal and status in the same local paper entry. Fuzzy
lineage evidence requires at least 70% of the agenda title's distinctive terms, a strong local title
match, no more than 15 tokens between the matched title span and status, and all other conference
coauthor surnames nearby. Multiple URLs from one author count as one source. Dense CV adjacency cases
are explicitly rejected; for example, a status attached to the next paper cannot be promoted merely
because the preceding agenda title also appears on the page.

Renamed-publication candidates are searched by up to three coauthors plus distinctive agenda-title
terms, restricted to post-conference journal records, and checked with Crossref/DOI metadata,
OpenAlex abstracts where available, and the first pages of the conference and candidate PDFs for
title-history notes. Curated title changes are stored in `data/renamed_lineage_confirmed.json` and
propagated to repeated exact-title appearances only when their author lineages agree.

## Evidence levels

The dashboard exposes the `verification` field as a filter and includes it in the download:

- `multiple_authors_cross_checked`: at least two distinct coauthors independently support the displayed publication/R&R.
- `cross_checked_author_source`: a current author CV or research page supports the displayed publication/R&R.
- `cross_checked_renamed_lineage`: a reviewed same-project title change supports the journal placement.
- `cross_checked_prior_research`: retained from earlier cross-checked project research.
- `official_nber_published`: the official NBER working-paper page lists the publication.
- `automated_crossref`: a high-confidence title-and-author journal metadata match.
- `exhaustively_checked_no_verified_status`: the paper remains a working paper after the complete fixed-point audit.

There are no remaining `provisional` rows. “Exhaustively checked” means every available method was
attempted and every generated lead was decided; it does not turn unavailable providers into evidence
that no publication exists.

## Metrics and comparisons

The dashboard uses one row per paper appearance. Program comparisons use only years represented by
both selected series and can be restricted to a contiguous subset of their shared years. The
all-program status and journal charts sum appearances across included programs within each year;
selecting a program switches to that program's cohorts.

Publication lag is the journal issue year minus the Summer Institute presentation year. Accepted or
forthcoming papers without an issue year count as published but are excluded from lag statistics.
R&Rs are excluded from journal-placement charts unless the **Count R&Rs** toggle is selected. Papers
published before their SI presentation retain a negative lag rather than being silently dropped.

## Rebuild and refresh

For a cached, deterministic rebuild and fixed-point verification:

```bash
python3 scripts/run_nber_si_exhaustive_audit.py --max-cycles 2
python3 -m unittest discover -s tests -v
```

For a newly collected year or an authorized external refresh:

```bash
python3 scripts/collect_nber_si.py
python3 scripts/enrich_nber_si.py --lookup
python3 scripts/run_nber_si_exhaustive_audit.py --network --max-cycles 0 --pdf
python3 -m unittest discover -s tests -v
```

Discovery scripts generate candidates; only reviewed decision applicators change publication status.
Raw NBER, Scholar, Crossref, author-page, and PDF responses are cached under `nber_si/cache/` and are
not committed. Normalized agenda rows, enriched JSON/CSV, audit ledgers, and the self-contained
dashboard are versioned.
