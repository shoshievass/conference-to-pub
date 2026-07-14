# conference-to-pub

Tracks where papers presented at six applied-micro / IO economics conferences ended up
being published:

1. **NBER Summer Institute — Industrial Organization** (2015–2026), programs scraped from
   `conference.nber.org/agenda/simple_printable?conf_id=SI{YY}IO`
2. **NBER Industrial Organization Program Meeting (Spring)** (2012–2026), scraped from
   `conference.nber.org/agenda/simple_printable?conf_id=IOs{YY}`
3. **Cowles Foundation — Structural Microeconomics / Models & Measurement**
   (paper-level coverage 2016–2019 and 2021–2026), scraped from the
   [Cowles conference archive](https://cowles.yale.edu/events/conferences), archived
   Structural Microeconomics agendas, and the individual Models & Measurement agendas
4. **Utah Winter Business Economics Conference** (2010–2026), scraped from
   [marriner.eccles.utah.edu](https://marriner.eccles.utah.edu/utah-winter-economics-conference/)
   (all years are inlined on that single page)
5. **FTC Microeconomics Conference** (2008–2024 and 2026), from the
   [FTC conference archive](https://www.ftc.gov/microeconomics) and official yearly agendas
6. **Northwestern Conference on Antitrust Economics and Competition Policy**
   (paper-level coverage 2011–2019 and 2021–2025), from Northwestern's
   [current](https://www.law.northwestern.edu/research-faculty/clbe/events/antitrust/) and
   [past-conference](https://www.law.northwestern.edu/research-faculty/clbe/events/antitrust/past.html/)
   pages

To add more conferences, follow [ADDING_A_CONFERENCE.md](ADDING_A_CONFERENCE.md).

For each paper on each agenda, the publication outcome (published/accepted at a journal,
under revise-and-resubmit, or still a working paper) was researched by web search in
**July 2026**.
Working-paper series (NBER WP, SSRN, CEPR) are *not* counted as publications. An **R&R**
(revise-and-resubmit at a named journal) is broken out as its own status — it is not an
acceptance, so by default it is not counted as a journal placement, but the dashboard has a
toggle to include R&Rs (at their target journal) in the by-journal figures.

## Findings at a glance

Across **774 papers** (from the six conferences; a paper presented at more than one is
counted once per appearance): **486 published or accepted**, **90 under R&R**, and **198
working papers**. Most common landing spots: American
Economic Review, Journal of Political Economy, Review of Economic Studies, and Econometrica.
Median conference-to-print lag is **3 years**. Recent cohorts are mostly still working papers
or R&Rs by construction. Explore it all in
`dashboard/index.html` — filter by conference, status, journal, year, or free text. The full
reproducible top-five-journal, publication-lag, same-year-overlap, and cross-conference
recurrence tables are in [`data/SUMMARY_STATS.md`](data/SUMMARY_STATS.md).

## Layout

```
data/
  papers.json           # master agenda list: one entry per paper per conference-year
  lookups/batch-*.json  # raw publication-lookup results (one file per research batch)
  papers_enriched.json  # merged + normalized (journal names canonicalized)
  papers_enriched.csv   # same, flat CSV
scripts/
  build_dashboard.py    # merges lookups into papers.json, writes enriched data + dashboard
  build_summary_stats.py # writes the cross-conference summary-statistics tables
dashboard/
  template.html         # dashboard source (data placeholder)
  index.html            # generated, self-contained — open directly in a browser
ADDING_A_CONFERENCE.md  # runbook for adding another conference to the pipeline
```

## Usage

```bash
python3 scripts/build_dashboard.py   # regenerate enriched data + dashboard/index.html
open dashboard/index.html
```

The dashboard supports filtering by conference, publication status (published / R&R / working
paper), journal, year, and free-text search, plus a checkbox to count R&Rs in the journal
figures. Choose a conference and then a second conference to compare them side by side; the
comparison automatically uses only years represented in both conferences. It shows
an optional contiguous start/end-year window for narrowing that shared-year comparison,
status-by-cohort stacked bars, the same cohorts
re-stacked and colored by journal (top 8 journals named, rest grouped as "Other"), journal
counts, a conference-to-print lag histogram, and a year-by-year browsable paper list.

## Data caveats

- **Utah 2021** was cancelled (Covid). **Utah 2019**: the conference website's "2019
  Conference" section accidentally duplicates the 2018 program; the real 2019 program is
  included only to the extent it could be recovered from web archives.
- **NBER SI 2026** (July 23–24, 2026) had not met yet at compile time; **Utah 2026** met
  February 2026. Recent cohorts are mostly working papers by construction.
- The FTC held annual conferences from 2008 through 2024, skipped 2025, and resumed in
  2026. The 2026 policy-and-research session is excluded because it was not an academic
  paper session.
- Northwestern's series began in 2008 and skipped 2020. Its live archive exposes complete
  paper lists from 2011 onward; the 2008–2010 event listings survive, but their paper-level
  programs could not be recovered, so those three editions are not represented here.
- Cowles's predecessor series was called Structural Microeconomics. Its complete 2016–2019
  agendas are combined with Models & Measurement as one Cowles series. The 2020 Cowles
  edition is not yet represented.
- Utah agendas list only the *presenter*; full author lists were filled in from the
  published/working-paper versions where found.
- Projects for which no public manuscript or published version was located are conservatively
  grouped with working papers; their evidence notes retain that distinction.
- Journal years refer to the journal *issue* year, which can trail online-first publication.
- **R&R** status (and the target journal) is read from each paper's lookup `note` and applied
  in `build_dashboard.py` via an explicit `RR_JOURNAL` map; "reject-and-resubmit" is grouped
  with R&R. R&R reflects the most recent status found (as of July 2026) and can go stale fast.
- Every paper left in the working-paper category received an author-CV/research-page recheck;
  see [`data/WORKING_PAPER_CV_AUDIT.md`](data/WORKING_PAPER_CV_AUDIT.md). "Under review" and
  an R&R with no disclosed target journal remain working papers under the project's rules.
