# NBER Summer Institute program dashboard

This is a separate companion to the project's IO-conference dashboard. It follows papers
presented across the NBER Summer Institute's different program meetings and workshops from
2015 through 2026.

## Methodology

### Agenda collection

`scripts/collect_nber_si.py` starts from each official annual NBER Summer Institute schedule,
discovers every linked meeting, reads the meeting's public NBER conference API, and retains
agenda items with an actual paper record. Breaks, welcomes, meals, and panels or lectures with
no paper record are excluded. The collector preserves the official meeting title, date, authors,
paper link, NBER working-paper number when present, and source URL.

Obvious title changes are joined into recurring series (for example, **Children** with
**Children and Families**, and the IT/digitization sequence with **Digital Economics and
Artificial Intelligence**). Distinct workshops are not silently merged simply because they are
related to the same broad NBER program. Both the canonical program and official meeting title
remain in the downloadable data.

### Publication matching

The status snapshot is dated **July 14, 2026** and uses the same three dashboard outcomes:

- **Published** includes published, accepted, and forthcoming journal articles.
- **R&R** is a named-journal revise-and-resubmit, major revision, or revision requested.
- **Working paper** means no publication, acceptance, or named-journal R&R has yet been verified.

`scripts/enrich_nber_si.py` first reuses cross-checked title matches from the original
conference-to-publication project. For rows with an NBER working-paper number, it next reads the
official NBER page's **Published Versions** record. It then searches Crossref journal-article
records and accepts only high-confidence title-and-author matches. Working-paper series such as
NBER, CEPR, and SSRN are not publications.

Every row has a `verification` field:

- **Multiple authors cross-checked** (`multiple_authors_cross_checked`): two or more distinct coauthors' CVs or research pages
  independently support the displayed classification. For an R&R or acceptance, the sources
  report the same named-journal status. For a working paper, the exact title appears on multiple
  author sources and none displays a named-journal R&R, acceptance, or forthcoming label.
- **Cross-checked against prior research** (`cross_checked_prior_research`): inherited from the project's publication/R&R and author-CV research.
- **Cross-checked against an author source** (`cross_checked_author_source`): confirmed from a linked author's current CV or research page.
- **Author source checked — no named status** (`author_page_checked_no_named_status`): the exact title was found on one linked current author
  page/CV, but no named-journal R&R, acceptance, or forthcoming label was detected with it.
- **Official NBER publication record** (`official_nber_published`): publication metadata listed on the official NBER working-paper page.
- **Automated Crossref match** (`automated_crossref`): a high-confidence title-and-author journal-metadata match that has
  not necessarily been individually source-reviewed.
- **Unresolved — no matched author evidence** (`provisional`): no high-confidence journal record or exact-title
  author-source evidence was found in the automated and author-source passes. The row is displayed as a working
  paper for the three-way metric, but this is uncertainty rather than proof of current working-paper status.

The dashboard exposes this evidence level as a filter and the CSV download preserves it. This
prevents an unmatched automated search from being presented as if it were a completed CV audit.

### Author-CV and research-page audit

The July 2026 working-paper recheck starts from the author objects on the official NBER agendas.
`scripts/audit_nber_si_cvs.py` checked 6,542 official NBER author profiles in the current audit queue,
discovered 1,802 linked author/institutional pages, and inspected 1,551 strong CV/vita documents as
well as visible research pages. Cached fetch errors are retried on later passes rather than treated as
completed checks.
Exact paper titles were matched to nearby status language. A named journal is required for an R&R;
generic “under review” language does not qualify.

Multiple URLs belonging to the same author count only once. The multiple-author tier therefore
requires independent evidence from at least two distinct coauthors, not a personal page plus that
same author's CV. In this snapshot it covers **101 paper appearances**: 97 working-paper
appearances across 84 title lineages, plus four appearances across two R&R title lineages
independently reported by multiple coauthors.

Automated candidates were manually reviewed because dense CV lists can otherwise assign the next
project's status to the preceding title. The curated decisions are in `data/cv_audit.json`; a
56-title rejection guardrail prevents known adjacency or conflict errors from being silently
reintroduced, including 49 candidates that recurred in the current pass. This pass confirmed 149
R&R title lineages and two newer acceptances, representing 187 SI appearances. It also found 696
still-working-paper appearances whose exact title was present on at least one author page/CV with no
named-journal R&R, acceptance, or forthcoming phrase attached.

A second publication-matching pass normalizes Unicode punctuation, apostrophes, hyphenation, HTML
entities, and initialisms before comparing titles. It recovered **175 published appearances across
162 distinct titles** that the stricter first pass had missed. Relaxed title matches still require
overlapping authors and journal-article metadata. Six newly surfaced R&R candidates were individually
reviewed and rejected because the journal status belonged to an adjacent project on the author CV or
research page, so the stronger pass did not inflate the R&R count.

Google Scholar was tried as a discovery-only layer for older unresolved titles. Direct Scholar
queries quickly hit rate limits, and the results primarily surfaced working-paper PDFs rather than
publication status. One title-history lead was verified against an official NBER Published Versions
record and stored in `data/scholar_verified_publications.json`; Scholar snippets alone are not used
as status evidence.

Verified outcomes are also propagated across repeated exact-title appearances when at least two
author surnames match (or the same sole author appears on both). This fixed one case in which the
same nursing-home private-equity paper was published in one program's row but still shown as a
working paper in another program's row.

After these passes, **3,802 appearances across 3,416 titles** remain `provisional`. This machine code
is displayed to readers as “Unresolved — no matched author evidence”; it means no exact evidence was
matched, not that no source lookup was attempted.

### Metrics and comparisons

The dashboard uses one row per paper appearance. A paper presented in two SI programs contributes
one appearance to each program. Program comparisons use only years represented by both selected
series and can be restricted to a contiguous subset of their shared years. Publication lag is the
journal issue year minus the Summer Institute year. R&Rs are excluded from journal-placement charts
unless the “Count R&Rs” toggle is selected. The all-program status and journal charts sum appearances
across included programs within each year; selecting a program switches to that program's cohorts.
Papers published before their SI presentation retain a negative lag. Accepted or forthcoming papers
without an issue year count as published but are excluded from lag statistics.

### Rebuild

```bash
python3 scripts/collect_nber_si.py
python3 scripts/enrich_nber_si.py --lookup
python3 scripts/build_nber_si_dashboard.py
python3 -m unittest discover -s tests -v
```

To refresh the author-source audit itself after collecting and enriching, run
`python3 scripts/audit_nber_si_cvs.py --external --documents`, review the generated candidates,
then run `python3 scripts/apply_nber_si_cv_audit.py` and enrich again. The manual review boundary is
intentional because dense CV layouts can create adjacent-project false positives.

To refresh the Google Scholar discovery sample, run
`python3 scripts/audit_nber_si_scholar.py --limit 25`, review `data/scholar_audit_candidates.json`,
and only add entries to `data/scholar_verified_publications.json` after confirming them against an
official NBER, publisher, DOI, or author source.

Raw official responses, Scholar pages, and Crossref results are cached under `nber_si/cache/` and are
not committed. Normalized agenda rows, enriched JSON/CSV, and the self-contained dashboard are
versioned.
