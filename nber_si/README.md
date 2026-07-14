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
- **Automated Crossref match** (`automated_crossref`): a high-confidence journal-metadata match that should still receive a
  final spot audit.
- **Provisional — author audit pending** (`provisional`): no verified journal match in the automated pass; an author-CV/R&R check is
  still pending, so this is provisionally displayed as a working paper.

The dashboard exposes this evidence level as a filter and the CSV download preserves it. This
prevents an unmatched automated search from being presented as if it were a completed CV audit.

### Author-CV and research-page audit

The July 2026 working-paper recheck starts from the author objects on the official NBER agendas.
`scripts/audit_nber_si_cvs.py` cached 6,822 official NBER author profiles, discovered 1,880 linked
author/institutional pages, and inspected strong CV/vita links as well as visible research pages.
Exact paper titles were matched to nearby status language. A named journal is required for an R&R;
generic “under review” language does not qualify.

Multiple URLs belonging to the same author count only once. The multiple-author tier therefore
requires independent evidence from at least two distinct coauthors, not a personal page plus that
same author's CV. In this snapshot it covers **102 paper appearances**: 98 working-paper
appearances across 85 title lineages, plus four appearances across two R&R title lineages
independently reported by multiple coauthors.

Automated candidates were manually reviewed because dense CV lists can otherwise assign the next
project's status to the preceding title. The curated decisions are in `data/cv_audit.json`; 50
known adjacency or conflict errors are preserved in `data/cv_audit_rejected_candidates.json` so a
rebuild cannot silently reintroduce them. This pass confirmed 149 R&R title lineages and two newer
acceptances, representing 187 SI appearances. It also found 728 still-working-paper appearances
whose exact title was present on an author page/CV with no named-journal R&R, acceptance, or
forthcoming phrase attached. Rows with no accessible or matched author source remain `provisional`.

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

Raw official responses and Crossref results are cached under `nber_si/cache/` and are not committed.
Normalized agenda rows, enriched JSON/CSV, and the self-contained dashboard are versioned.
