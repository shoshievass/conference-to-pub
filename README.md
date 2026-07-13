# conference-to-pub

Tracks where papers presented at two economics conferences ended up being published:

1. **NBER Summer Institute — Industrial Organization** (2015–2026), programs scraped from
   `conference.nber.org/agenda/simple_printable?conf_id=SI{YY}IO`
2. **Utah Winter Business Economics Conference** (2010–2026), programs scraped from
   [marriner.eccles.utah.edu](https://marriner.eccles.utah.edu/utah-winter-economics-conference/)
   (all years are inlined on that single page)

For each paper on each agenda, the publication outcome (journal + year, forthcoming, or
still a working paper) was researched by web search in **July 2026**. Working-paper series
(NBER WP, SSRN, CEPR) are *not* counted as publications.

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
```

## Usage

```bash
python3 scripts/build_dashboard.py   # regenerate enriched data + dashboard/index.html
open dashboard/index.html
```

The dashboard supports filtering by conference, publication status, journal, year, and
free-text search; it shows status-by-cohort stacked bars, journal counts, a
conference-to-print lag histogram, and a year-by-year browsable paper list.

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
