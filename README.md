# conference-to-pub

Tracks where papers presented at four applied-micro / IO economics conferences ended up
being published:

1. **NBER Summer Institute — Industrial Organization** (2015–2026), programs scraped from
   `conference.nber.org/agenda/simple_printable?conf_id=SI{YY}IO`
2. **NBER Industrial Organization Program Meeting (Spring)** (2012–2026), scraped from
   `conference.nber.org/agenda/simple_printable?conf_id=IOs{YY}`
3. **Cowles Foundation — Conference on Models & Measurement** (2025–2026), scraped from
   [cowles.yale.edu](https://cowles.yale.edu/conferences/models-measurement/2026)
4. **Utah Winter Business Economics Conference** (2010–2026), scraped from
   [marriner.eccles.utah.edu](https://marriner.eccles.utah.edu/utah-winter-economics-conference/)
   (all years are inlined on that single page)

To add more conferences, follow [ADDING_A_CONFERENCE.md](ADDING_A_CONFERENCE.md).

For each paper on each agenda, the publication outcome (journal + year, forthcoming, under
revise-and-resubmit, or still a working paper) was researched by web search in **July 2026**.
Working-paper series (NBER WP, SSRN, CEPR) are *not* counted as publications. An **R&R**
(revise-and-resubmit at a named journal) is broken out as its own status — it is not an
acceptance, so by default it is not counted as a journal placement, but the dashboard has a
toggle to include R&Rs (at their target journal) in the by-journal figures.

## Findings at a glance

Across **393 papers** (from the four conferences; a paper presented at more than one is
counted once per appearance): **211 published**, **27 forthcoming**, **59 under R&R** at a
journal, **94 still working papers**, **2 not found**. Most common landing spots: American
Economic Review, Journal of Political Economy, Review of Economic Studies, and Econometrica.
Median conference-to-print lag is **3 years**. Recent cohorts (and Cowles M&M, which only
exists from 2025) are mostly still working papers or R&Rs by construction. Explore it all in
`dashboard/index.html` — filter by conference, status, journal, year, or free text.

## Layout

```
data/
  papers.json           # master agenda list: one entry per paper per conference-year
  lookups/batch-*.json  # raw publication-lookup results (one file per research batch)
  papers_enriched.json  # merged + normalized (journal names canonicalized)
  papers_enriched.csv   # same, flat CSV
scripts/
  build_dashboard.py    # merges lookups into papers.json, writes enriched data + dashboard
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

The dashboard supports filtering by conference, publication status (published / forthcoming /
R&R / working paper / not found), journal, year, and free-text search, plus a checkbox to
count R&Rs in the journal figures. It shows status-by-cohort stacked bars, the same cohorts
re-stacked and colored by journal (top 8 journals named, rest grouped as "Other"), journal
counts, a conference-to-print lag histogram, and a year-by-year browsable paper list.

## Data caveats

- **Utah 2021** was cancelled (Covid). **Utah 2019**: the conference website's "2019
  Conference" section accidentally duplicates the 2018 program; the real 2019 program is
  included only to the extent it could be recovered from web archives.
- **NBER SI 2026** (July 23–24, 2026) had not met yet at compile time; **Utah 2026** met
  February 2026. Recent cohorts are mostly working papers by construction.
- Utah agendas list only the *presenter*; full author lists were filled in from the
  published/working-paper versions where found.
- "Not found" means no published version was located by search — not proof none exists.
- Journal years refer to the journal *issue* year, which can trail online-first publication.
- **R&R** status (and the target journal) is read from each paper's lookup `note` and applied
  in `build_dashboard.py` via an explicit `RR_JOURNAL` map; "reject-and-resubmit" is grouped
  with R&R. R&R reflects the most recent status found (as of July 2026) and can go stale fast.
