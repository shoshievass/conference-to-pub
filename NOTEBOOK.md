# Lab notebook — conference-to-pub

## 2026-07-13 — initial build

**Goal.** For every paper on the agendas of (1) NBER SI Industrial Organization and
(2) the Utah Winter Business Economics Conference, find where/when it was published;
build a dashboard to scan papers by year with summary figures.

**Scraping path (what worked / didn't):**
- Utah page (`marriner.eccles.utah.edu/utah-winter-economics-conference/`): 403 to plain
  fetchers, but plain `curl` with a browser User-Agent works. Bonus: *every* year
  2010–2026 is inlined on the one page — no archive crawling needed.
- NBER conference pages load the agenda dynamically. The underlying endpoint is
  `https://conference.nber.org/agenda/simple_printable?conf_id=SI{YY}IO` — but it 403s
  for curl *and* WebFetch (bot detection). Solution: load one page in a real browser
  pane, then `fetch()` the other years same-origin from the page context. All of
  SI15IO–SI26IO exist; SI13IO/SI14IO return only a header stub (no papers listed).
- **Utah 2019 gotcha:** the site's "2019 Conference" section is a verbatim duplicate of
  the 2018 program (site bug — the award list confirms a distinct 2019 happened, Zitzewitz
  award to Ryan Kellogg). Attempted recovery via Wayback Machine (batch-18).
- Utah 2021 cancelled (Covid) — the award list literally names "Covid-19 (2021)" as winner.

**Publication lookups.** 249 agenda papers split into 17 batches (~15 papers each), each
researched by a parallel web-search agent; results in `data/lookups/batch-*.json`.
Ground rules: only real peer-reviewed journals count as published (NBER/SSRN WPs do not);
"forthcoming" requires official acceptance, R&R does not count; verify journal+year
against a publisher page or author CV, not memory. Utah agendas name only presenters, so
agents also recovered full author lists.

**Normalization.** `scripts/build_dashboard.py` canonicalizes journal-name variants
(AER/QJE/JPE abbreviations, "The ..." prefixes, AEJ subtitles) via an explicit map, and
derives `lag = pub_year − conference_year` for published papers.

**Known limitations.**
- Presenter-only Utah listings mean early-year author lists depend on the lookup agent
  finding the right paper; titles that changed a lot before publication are the risk case.
- "Published year" is the issue year, so lag slightly overstates for online-first papers.
- Some working papers have R&R status noted in `note` but are still classed working_paper.

## 2026-07-13 — finishing the run

**What was left.** The first session stopped mid-lookup: only 192 of 249 papers had lookups
(batches 01–12, 14). The 57 missing were all Utah cohorts 2016–2026. Re-ran the four
interrupted batches with parallel web-search agents:
- batch-13 = Utah 2016–2017 (15), batch-15 = Utah 2020–2023 (15),
  batch-16 = Utah 2023–2025 (15), batch-17 = Utah 2025–2026 (12).
All 249 papers now covered exactly once (verified: no gaps, dupes, or schema holes).
The notebook's earlier "batch-18 / Utah 2019 recovery" never yielded papers — the Wayback
copy was unusable, so there are no `utah2019` rows and none were fabricated.

**Two template bugs found only by actually rendering the dashboard** (index.html had never
been generated + opened before):
1. `dashboard/template.html` had no `<meta charset>`. Served without a charset, accented
   author names (Hortaçsu, Bénabou, Antón…) mis-decoded and the title arrow showed as
   mojibake. Added `<meta charset="utf-8">` + a viewport tag.
2. A **truncated ternary** in `renderTiles`: `rows.length ? Math.round(…)+"%"` was missing
   its `: "—"` else-branch, so the *entire* `<script>` failed to parse and every chart,
   tile, and the paper list rendered blank (no console error — silent parse failure).
   Diagnosed by fetching the script into `new Function()` in the browser to get the line/col
   (line 47, "Unexpected token ','"). Added the missing `: "—"`. Lesson: a self-contained
   HTML dashboard must be opened in a browser as part of "done," not just built.

**Final tally (web search, July 2026):** 249 papers → 140 published, 16 forthcoming,
91 working paper, 2 not found. Top venues: AER 29, JPE 28, RESTUD 21, Econometrica 13.
Median conference-to-print lag 3 years. Dashboard verified rendering + filters (status,
journal, year, free-text search) working in a browser.

**Note on cross-listed papers.** A few papers appear on both agendas in different years
(e.g. "Common Ownership, Competition, and Top Management Incentives" = `utah2017-04` and
`nber2021-04`); both rows resolve to the same outcome (JPE 2023) — confirmed consistent.

**Second chart — "Journal placement by conference year."** Added a stacked bar that mirrors
the status-by-year chart's cohort layout (NBER/Utah pairs) but colors segments by journal
instead of status; bar height = published+forthcoming papers in that cohort. There's a clean
count break after the top 8 journals (each ≥6 papers, together 127/156 placed), so those 8
are named and the remaining 18 fold into a neutral "Other" — following the dataviz rule that
a 9th category is never a new hue. Colors are the reference categorical palette (already the
dashboard's design system), assigned to journals by *global* rank so a journal keeps its
color under filtering (color follows the entity, not its post-filter rank). Dark-mode
adjacent-color separation is in the palette's floor band, mitigated by the 2px inter-segment
surface gaps + always-on legend + hover tooltips. Verified in a browser in both themes.

**R&R as a first-class status + a journal-count toggle.** The lookups (per the original rules)
buried revise-and-resubmit outcomes inside `working_paper` with the target journal only in the
`note`. Grepping the notes found **27 R&R papers** (incl. "reject-and-resubmit", which I group
with R&R). Rather than rewrite the raw batch files, I added an explicit `RR_JOURNAL` map (id →
target journal, read off the notes) to `build_dashboard.py`; the normalization layer promotes
those to a new `rr` status and sets `journal` to the R&R target (no `pub_year`). New split:
140 published / 16 forthcoming / **27 R&R** / 64 working / 2 not found. Dashboard: R&R is a
distinct violet status segment + filter option (violet #4a3aa7 / dark #9085e9 — clear of the
blue "forthcoming" and yellow "working" it sits between; it does collide with the *journal*
chart's AEJ:Micro violet, but the two charts have separate legends). A "Count R&Rs in journal
figures" checkbox (off by default — an R&R isn't an acceptance) folds R&R papers, at their
target journal, into both journal charts + the distinct-journals tile; e.g. AER 29 → 40 with it
on. The named top-8 journal set is computed over published+forthcoming+R&R so colors stay put
when the toggle flips. Verified: toggle on/off, R&R filter (27 rows), tiles, notes all update.

**CV recheck of the non-R&R working papers → 8 more R&Rs.** Ran a fresh pass over all 64
plain working papers (5 parallel agents), checking each paper's *authors'* CVs / faculty
pages / Google Scholar for a status the first pass missed. Rules: "R&R" includes "major/minor
revision", "revision requested", "reject and resubmit", 2nd-round R&R; but "under review" /
"submitted" does NOT (no revision invited yet). Found **8** working papers actually under R&R,
each verified on a coauthor's own page: nber2016-06 (JPE, "major revision"), nber2019-05 (JPE,
"revision requested"), nber2023-03 (QJE), nber2024-02 (Econometrica, 2nd-round — was logged as
"under review"), nber2025-07 (JPE), nber2026-07 (AER), utah2025-06 (Econometrica), utah2026-03
(AER). Added them to `RR_JOURNAL`; gave each a fresh `RR_NOTE` (build script) so the displayed
note reflects the recheck instead of the stale "no journal version found". New split: 140
published / 16 forthcoming / **35 R&R** / 56 working / 2 not found; AER with R&Rs on → 42. No
working paper turned out to be already published/forthcoming. Agents also caught two
confabulations by verifying against author pages (a false "JLE" claim for Azar-Berry-Marinescu;
a false "forthcoming JET" for Pavan-Tirole — the JET label belonged to a different Pavan paper).
Process note: one chunk agent spawned its own sub-agents instead of researching directly and
wrote no file; re-ran that chunk directly. Reconciled by coverage (all 64 ids present, no dupes).
