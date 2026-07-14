# Publication attribution audit

Audit date: 2026-07-13  
Dataset audited: `data/papers_enriched.json`  
Coverage: 393 of 393 existing IDs

## Outcome

No title-to-publication or journal-attribution correction was found. The existing matches and cross-listed-paper reuse are internally consistent and supported by the source-specific notes already stored with every row. One status correction was made after enforcing the named-journal R&R rule.

There are 30 corrections in `data/audit_corrections.json`:

- 27 `forthcoming` rows become `published`, because accepted, conditionally accepted, article-in-advance, and forthcoming papers now share the `published` category.
- 2 `not_found` rows become `working_paper`, because the dashboard now permits only `working_paper`, `rr`, and `published`. Their notes continue to say that no public manuscript was located.
- 1 unnamed R&R (`iosp2019-02`) becomes `working_paper`, because no target journal is disclosed.
- 363 rows retain their existing status and attribution.
- Title/journal attribution corrections: 0; status-rule corrections: 1.

The correction file uses the standard lookup schema (`id`, `status`, `journal`, `pub_year`, `published_title`, `authors`, `url`, `note`) and labels every changed row as taxonomy normalization only.

## Coverage and evidence

Original status coverage:

| Original status | Rows | Normalized action |
|---|---:|---|
| published | 211 | retain |
| forthcoming | 27 | map to published |
| rr | 59 | retain 58; map 1 unnamed R&R to working paper |
| working_paper | 94 | retain |
| not_found | 2 | map to working_paper |
| **Total** | **393** | **393 accounted for** |

All 393 rows have an evidence note. All 296 placed rows (211 published, 27 forthcoming/accepted, 58 named-journal R&Rs) have both a nonempty URL and a nonempty note.

The placed-paper URLs are concentrated on primary publisher hosts: AEA (62), Oxford Academic (50), Wiley (35), University of Chicago Press (34), INFORMS (14), ScienceDirect/Elsevier (8), Springer (3), plus six DOI resolver links and smaller publisher hosts. The remaining placed-paper evidence uses NBER (37), SSRN (10), or author/CV/research pages, mainly for R&R and accepted-but-not-yet-issue-assigned records.

Fresh high-risk checks agreed with the stored attributions:

- Thomas Wollmann's January 2026 CV still lists “Effects of Regulatory Capture” as R&R at AEJ: Economic Policy and “How to Get Away with Merger” as accepted at JPE: https://questromworld.bu.edu/thomas-wollmann/wp-content/uploads/sites/70/2026/04/cv_tgw_current.pdf
- Daniel Mangrum's current research page still lists “The Marginal Congestion of a Taxi in New York City” as a second-round AER R&R: https://www.danielmangrum.com/research.html
- NBER continues to identify “From Revolving Doors to Regulatory Capture?” as working paper 24638, revised July 2024: https://www.nber.org/papers/w24638

These checks target old R&R records, which are the records most likely to have advanced since an earlier audit. Recent accepted/advance-access records were already tied to publisher or author sources dated through July 2026.

## Automated consistency checks

The audit found:

- 0 duplicate IDs.
- 0 published rows missing journal, publication year, or URL.
- 0 published rows whose `lag` differs from `pub_year - conference_year`.
- 0 published rows with a negative lag.
- 0 working-paper rows carrying journal, publication-year, or lag values.
- 0 R&R/forthcoming rows carrying publication-year or lag values.
- 0 conflicting exact-title duplicate clusters.
- 0 conflicting same-URL cross-listed clusters.

Ten exact-title cross-listed clusters were checked, including “Energy Transitions in Regulated Markets,” “Vertical Integration and Consumer Choice,” “Targeting and Price Pass-Through,” and the repeated Utah/NBER Spring papers. The retitled duplicate represented by NBER WP 30542 was also consistent across its two conference records.

The formerly unnamed R&R (`iosp2019-02`) is now a working paper: the author page discloses “Revise and Resubmit” but not the journal, and this project requires a named target journal for R&R status.

## Scope note

This is an audit of the 393 rows that existed at the start of that task. The later Cowles,
FTC, and Northwestern additions—and a fresh author-CV/research-page pass over every row still
classified as a working paper—are covered in `data/WORKING_PAPER_CV_AUDIT.md`.

## ID coverage manifest

Every original ID appears exactly once below, grouped by its pre-normalization status.

### forthcoming (27)

cowles2026-10, iosp2019-05, iosp2021-08, iosp2022-01, iosp2023-10, iosp2024-01, iosp2024-04, iosp2024-05, iosp2024-06, iosp2024-08, iosp2025-06, nber2016-04, nber2018-14, nber2019-01, nber2020-07, nber2021-07, nber2021-10, nber2022-09, nber2022-13, nber2023-09, nber2023-11, nber2024-06, nber2025-03, nber2025-08, utah2014-08, utah2017-06, utah2024-02

### not_found (2)

nber2015-01, nber2026-06

### published (211)

iosp2012-02, iosp2012-03, iosp2012-04, iosp2013-01, iosp2013-02, iosp2013-03, iosp2013-04, iosp2014-01, iosp2014-02, iosp2014-03, iosp2014-04, iosp2014-06, iosp2014-07, iosp2015-01, iosp2015-02, iosp2015-03, iosp2015-04, iosp2015-05, iosp2015-06, iosp2015-07, iosp2015-08, iosp2016-01, iosp2016-02, iosp2016-03, iosp2016-04, iosp2016-05, iosp2017-01, iosp2017-02, iosp2017-04, iosp2017-05, iosp2017-06, iosp2018-01, iosp2018-02, iosp2018-03, iosp2018-04, iosp2018-05, iosp2018-08, iosp2018-09, iosp2019-04, iosp2019-07, iosp2019-08, iosp2019-09, iosp2019-10, iosp2019-11, iosp2019-12, iosp2020-03, iosp2020-04, iosp2020-05, iosp2020-06, iosp2020-07, iosp2020-08, iosp2020-09, iosp2020-10, iosp2020-11, iosp2021-02, iosp2021-03, iosp2021-04, iosp2021-05, iosp2021-06, iosp2021-07, iosp2021-09, iosp2022-02, iosp2022-04, iosp2022-05, iosp2022-06, iosp2022-07, iosp2022-10, iosp2023-03, iosp2023-05, iosp2023-08, iosp2024-02, nber2015-02, nber2015-03, nber2015-04, nber2015-05, nber2015-06, nber2015-07, nber2015-08, nber2015-09, nber2016-01, nber2016-02, nber2016-03, nber2016-05, nber2016-07, nber2016-08, nber2017-01, nber2017-02, nber2017-04, nber2017-07, nber2017-09, nber2018-01, nber2018-02, nber2018-03, nber2018-04, nber2018-06, nber2018-07, nber2018-08, nber2018-09, nber2018-10, nber2018-11, nber2018-12, nber2018-13, nber2018-15, nber2019-02, nber2019-04, nber2019-06, nber2019-08, nber2020-03, nber2020-04, nber2020-05, nber2020-06, nber2020-08, nber2020-10, nber2021-01, nber2021-02, nber2021-03, nber2021-04, nber2021-05, nber2021-08, nber2021-09, nber2021-12, nber2022-01, nber2022-04, nber2022-06, nber2022-10, nber2022-12, nber2023-06, nber2024-01, nber2024-07, nber2024-10, nber2024-11, nber2025-05, utah2010-01, utah2010-02, utah2010-03, utah2010-04, utah2010-05, utah2010-06, utah2011-02, utah2011-03, utah2011-04, utah2011-06, utah2012-01, utah2012-02, utah2012-03, utah2012-04, utah2012-05, utah2012-06, utah2012-07, utah2012-08, utah2013-01, utah2013-02, utah2013-03, utah2013-04, utah2013-06, utah2013-07, utah2013-08, utah2014-01, utah2014-02, utah2014-03, utah2014-04, utah2014-05, utah2014-06, utah2014-07, utah2015-01, utah2015-02, utah2015-03, utah2015-04, utah2015-05, utah2015-06, utah2015-07, utah2015-08, utah2016-01, utah2016-02, utah2016-04, utah2016-05, utah2016-06, utah2017-01, utah2017-03, utah2017-04, utah2017-05, utah2017-07, utah2017-08, utah2018-01, utah2018-02, utah2018-03, utah2018-04, utah2018-05, utah2018-06, utah2018-07, utah2018-08, utah2020-01, utah2020-02, utah2020-04, utah2020-05, utah2020-06, utah2020-07, utah2020-08, utah2020-09, utah2022-02, utah2022-03, utah2022-04, utah2022-05, utah2022-08, utah2023-03, utah2023-05, utah2023-06, utah2024-01, utah2024-04, utah2024-05, utah2024-07

### rr (59)

cowles2025-01, cowles2025-03, cowles2025-07, cowles2025-10, iosp2016-07, iosp2019-01, iosp2019-02, iosp2019-03, iosp2020-01, iosp2021-01, iosp2022-08, iosp2023-02, iosp2023-04, iosp2023-07, iosp2023-09, iosp2024-07, iosp2025-01, iosp2025-05, iosp2025-07, iosp2025-09, iosp2026-02, iosp2026-03, iosp2026-04, iosp2026-08, nber2016-06, nber2017-06, nber2017-08, nber2018-05, nber2019-05, nber2019-09, nber2022-07, nber2023-01, nber2023-02, nber2023-03, nber2023-04, nber2023-07, nber2023-12, nber2023-13, nber2024-02, nber2024-03, nber2024-04, nber2024-08, nber2025-02, nber2025-04, nber2025-07, nber2025-10, nber2026-07, utah2016-08, utah2020-03, utah2022-07, utah2023-01, utah2023-02, utah2023-07, utah2024-03, utah2024-06, utah2025-02, utah2025-06, utah2025-08, utah2026-03

### working_paper (94)

cowles2025-02, cowles2025-04, cowles2025-05, cowles2025-06, cowles2025-08, cowles2025-09, cowles2026-01, cowles2026-02, cowles2026-03, cowles2026-04, cowles2026-05, cowles2026-06, cowles2026-07, cowles2026-08, cowles2026-09, iosp2012-01, iosp2014-05, iosp2016-06, iosp2017-03, iosp2018-06, iosp2018-07, iosp2019-06, iosp2020-02, iosp2022-03, iosp2022-09, iosp2022-11, iosp2023-01, iosp2023-06, iosp2024-03, iosp2025-02, iosp2025-03, iosp2025-04, iosp2025-08, iosp2026-01, iosp2026-05, iosp2026-06, iosp2026-07, iosp2026-09, nber2017-03, nber2017-05, nber2019-03, nber2019-07, nber2019-10, nber2020-01, nber2020-02, nber2020-09, nber2021-06, nber2021-11, nber2022-02, nber2022-03, nber2022-05, nber2022-08, nber2022-11, nber2023-05, nber2023-08, nber2023-10, nber2023-14, nber2024-05, nber2024-09, nber2025-01, nber2025-06, nber2025-09, nber2026-01, nber2026-02, nber2026-03, nber2026-04, nber2026-05, nber2026-08, nber2026-09, nber2026-10, nber2026-11, utah2011-01, utah2011-05, utah2013-05, utah2016-03, utah2016-07, utah2017-02, utah2022-01, utah2022-06, utah2023-04, utah2023-08, utah2024-08, utah2025-01, utah2025-03, utah2025-04, utah2025-05, utah2025-07, utah2026-01, utah2026-02, utah2026-04, utah2026-05, utah2026-06, utah2026-07, utah2026-08
