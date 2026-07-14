# Working-paper author-CV audit

Audit date: 2026-07-14  
Dataset before audit: 725 paper appearances  
Audit scope: every row then classified as `working_paper` (242 rows; 232 exact titles)

## Outcome

The CV/research-page pass changed 57 records:

- 52 working-paper records were matched to a journal publication or verified acceptance and
  are now `published`.
- 5 records are now `rr`, each with a named target journal.
- 185 records remain `working_paper`.

The rebuilt dashboard therefore contains **453 published/accepted, 87 R&R, and 185 working
paper appearances**. The batch-30 changes are encoded explicitly in
`scripts/apply_batch30_cv_audit.py` and applied to `data/lookups/batch-30.json`.

## Rules and method

- The starting manifest was the 242 rows not already `published` or `rr`. Exact duplicate
  titles were grouped, giving 232 distinct projects.
- The 114 rows from the earlier conference set retained the author-CV/research-page audit
  completed in July 2026. The 128 FTC and Northwestern rows received a fresh pass against an
  author's current CV or research page where available, then exact-title, DOI, publisher, and
  working-paper-series checks to resolve title changes.
- A named-journal revision invitation (including "revision requested," major/minor revision,
  or reject-and-resubmit) counts as `rr`. "Under review" or "submitted" does not.
- An author page that says only "R&R" without identifying the journal remains
  `working_paper`. This applies, for example, to `ftc2024-05`.
- Accepted, conditionally accepted, forthcoming, and online-ahead-of-issue papers are all
  `published`; the dashboard intentionally does not distinguish those substatuses.
- A superficially similar article was not enough to promote a row. The authors, empirical or
  theoretical project, and title/version trail had to identify the same paper.

## Newly verified named-journal R&Rs

| ID | Conference title | Target | Author evidence |
|---|---|---|---|
| `ftc2015-05` | Generalized Insurer Bargaining | AEJ: Microeconomics | Paul Grieco CV; last located explicit status |
| `ftc2023-06` | Regulating the Innovators | Journal of Political Economy | Parker Rogers research page |
| `ftc2024-01` | Driving the Drivers | International Journal of Industrial Organization | Yanyou Chen research page: "Revision requested at IJIO" |
| `ftc2024-02` | Dynamic Monopsony with Large Firms and Noncompetes | Econometrica | Gregor Jarosch research page |
| `nwae2024-03` | Painful Bargaining | American Economic Review | Thomas Wollmann research page, May 2026 |

## High-risk checks that remained working papers

- `ftc2008-01`, *The Welfare Effects of Ticket Resale*: the exact working paper was revised
  again in April 2026. It is not the separately published *Resale and Rent-Seeking*.
- `ftc2008-03`, *Testing Theories of Price Dispersion and Scarcity Pricing in the Airline
  Industry*: author and later-literature records still identify the exact paper as a mimeo.
  The Puller-Taylor day-of-week price-discrimination article is a different project.
- `ftc2013-02` and `ftc2014-07`: Christopher Conlon's current CV says "under review," not R&R.
- `ftc2018-05`, *Diagnosing Price Dispersion*: Ashley Swanson's current page lists it as
  research in progress.
- `ftc2022-02`, *Dynamic Price Competition*: Kevin Williams' CV calls it a permanent/resting
  working paper.
- `nwae2011-02`, *Exclusionary Minimum Resale Price Maintenance*: the exact SSRN paper was
  revised in April 2025 but has no named-journal R&R.
- `nwae2019-01`: now titled *Optimal Merger Remedies* (August 2025), still a working paper.
- `nwae2022-02`: the current author page lists the retitled hospital/physician-acquisition
  project as a working paper, not an R&R.
- `nwae2025-02`, *Digital (Killer?) Acquisitions*: the current author page labels R&R status
  for another project but not this one, so the target remains a working paper.

## Retained-working coverage manifest

All 185 retained working-paper IDs appear below. This is the post-audit completeness check.

### Cowles M&M (32)

`cowles2021-10`, `cowles2021-12`, `cowles2022-02`, `cowles2022-04`, `cowles2022-05`,
`cowles2022-07`, `cowles2023-01`, `cowles2023-02`, `cowles2023-04`, `cowles2023-08`,
`cowles2023-10`, `cowles2024-01`, `cowles2024-02`, `cowles2024-03`, `cowles2024-05`,
`cowles2024-07`, `cowles2024-09`, `cowles2025-02`, `cowles2025-04`, `cowles2025-05`,
`cowles2025-06`, `cowles2025-08`, `cowles2025-09`, `cowles2026-01`, `cowles2026-02`,
`cowles2026-03`, `cowles2026-04`, `cowles2026-05`, `cowles2026-06`, `cowles2026-07`,
`cowles2026-08`, `cowles2026-09`.

### FTC Micro (39)

`ftc2008-01`, `ftc2008-03`, `ftc2008-06`, `ftc2008-09`, `ftc2009-02`, `ftc2009-05`,
`ftc2009-10`, `ftc2010-03`, `ftc2011-02`, `ftc2011-08`, `ftc2011-09`, `ftc2011-11`,
`ftc2012-09`, `ftc2013-02`, `ftc2013-07`, `ftc2014-07`, `ftc2015-02`, `ftc2015-07`,
`ftc2016-05`, `ftc2017-04`, `ftc2018-05`, `ftc2019-05`, `ftc2019-06`, `ftc2020-03`,
`ftc2020-05`, `ftc2020-07`, `ftc2020-08`, `ftc2021-02`, `ftc2022-02`, `ftc2022-05`,
`ftc2022-08`, `ftc2024-03`, `ftc2024-05`, `ftc2024-07`, `ftc2026-01`, `ftc2026-03`,
`ftc2026-06`, `ftc2026-07`, `ftc2026-09`.

### NBER IO Spring (24)

`iosp2012-01`, `iosp2014-05`, `iosp2016-06`, `iosp2017-03`, `iosp2018-06`, `iosp2018-07`,
`iosp2019-02`, `iosp2019-06`, `iosp2020-02`, `iosp2022-03`, `iosp2022-09`, `iosp2022-11`,
`iosp2023-01`, `iosp2023-06`, `iosp2024-03`, `iosp2025-02`, `iosp2025-03`, `iosp2025-04`,
`iosp2025-08`, `iosp2026-01`, `iosp2026-05`, `iosp2026-06`, `iosp2026-07`, `iosp2026-09`.

### NBER SI IO (35)

`nber2015-01`, `nber2017-03`, `nber2017-05`, `nber2019-03`, `nber2019-07`, `nber2019-10`,
`nber2020-01`, `nber2020-02`, `nber2020-09`, `nber2021-06`, `nber2021-11`, `nber2022-02`,
`nber2022-03`, `nber2022-05`, `nber2022-08`, `nber2022-11`, `nber2023-05`, `nber2023-08`,
`nber2023-10`, `nber2023-14`, `nber2024-05`, `nber2024-09`, `nber2025-01`, `nber2025-06`,
`nber2025-09`, `nber2026-01`, `nber2026-02`, `nber2026-03`, `nber2026-04`, `nber2026-05`,
`nber2026-06`, `nber2026-08`, `nber2026-09`, `nber2026-10`, `nber2026-11`.

### Northwestern Antitrust (32)

`nwae2011-01`, `nwae2011-02`, `nwae2011-03`, `nwae2011-07`, `nwae2012-01`, `nwae2012-05`,
`nwae2012-07`, `nwae2013-01`, `nwae2013-02`, `nwae2013-06`, `nwae2014-01`, `nwae2014-05`,
`nwae2015-01`, `nwae2015-06`, `nwae2016-01`, `nwae2016-04`, `nwae2016-09`, `nwae2017-01`,
`nwae2018-05`, `nwae2019-01`, `nwae2019-03`, `nwae2019-05`, `nwae2019-07`, `nwae2021-05`,
`nwae2022-01`, `nwae2022-02`, `nwae2022-07`, `nwae2023-06`, `nwae2024-02`, `nwae2024-06`,
`nwae2024-07`, `nwae2025-02`.

### Utah WBEC (23)

`utah2011-01`, `utah2011-05`, `utah2013-05`, `utah2016-03`, `utah2016-07`, `utah2017-02`,
`utah2022-01`, `utah2022-06`, `utah2023-04`, `utah2023-08`, `utah2024-08`, `utah2025-01`,
`utah2025-03`, `utah2025-04`, `utah2025-05`, `utah2025-07`, `utah2026-01`, `utah2026-02`,
`utah2026-04`, `utah2026-05`, `utah2026-06`, `utah2026-07`, `utah2026-08`.

## Consistency checks

- 725 unique IDs and 725 merged lookup rows.
- Only `published`, `rr`, and `working_paper` statuses remain.
- Every R&R has a named journal; every published record has a journal.
- No retained working paper carries a journal or publication year.
- No exact-title duplicate cluster disagrees on status, journal, or publication year.
- No batch-30 note still says "pending CV review."

## 2026-07-14 Cowles Structural Microeconomics addendum

The later Cowles backfill added 49 fully audited 2016–2019 appearances: 33 published, 3 R&R,
and 13 working papers. The 13 retained working-paper IDs are `cowles2016-02`,
`cowles2016-03`, `cowles2016-10`, `cowles2016-12`, `cowles2017-01`, `cowles2017-04`,
`cowles2017-08`, `cowles2018-01`, `cowles2018-02`, `cowles2018-12`, `cowles2019-08`,
`cowles2019-09`, and `cowles2019-12`. Each received the same author-CV/research-page check.
The current merged totals are **774 appearances: 486 published/accepted, 90 R&R, and 198
working papers**, with 774 unique IDs and 774 lookup rows.
