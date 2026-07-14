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

## 2026-07-13 — two more conferences (NBER IO Spring + Cowles M&M)

**Goal.** Add the NBER IO *Spring* program meetings and the Cowles *Models & Measurement*
conference with the same flow (scrape → lookups → CV recheck → dashboard), and write a
reusable runbook (`ADDING_A_CONFERENCE.md`).

**Scraping.**
- *NBER IO Spring*: same printable endpoint family as SI IO but `conf_id=IOs{YY}`. Curl/WebFetch
  still 403 → loaded `conference.nber.org` in the browser and `fetch()`ed all years same-origin.
  Content years IOs12–IOs26 (2012–2026; IOs05–11 are header-only stubs). Parsed titles from
  `<em>`, authors from `.author-name` (discussants excluded via `.discussant-name`), stripped
  ligature control-chars, deduped by title (2019 listed one paper 3×). **124 papers.**
- *Cowles M&M*: curl works (Yale, no bot wall). Agenda is a Time/Title/Presenter table inside
  `<details class="layout__details">`; two row formats (title in `<a>` + `Speaker:` in a
  `<span class="label">`, vs. title in `<h4>` + `Speaker:` in `<strong>`, trailing `*`). Only
  **2025 and 2026** exist under this name (earlier years 301). **20 papers**, presenter-only
  (coauthors recovered at lookup, like Utah).

**Reuse.** Matched new titles (normalized) against existing enriched outcomes → 7 exact
cross-listed reuses (copied outcome, noted source id). 137 needed fresh lookups.

**Lookups + CV check in one pass.** 10 parallel agents (batches 19–28), each doing the
combined lookup + CV/R&R check: statuses published/forthcoming/rr/working_paper/not_found,
R&R detected from author CVs (incl. major/minor revision, revision requested, reject-and-
resubmit, 2nd-round; NOT "under review"). Fixed a build-script bug so agent-written `rr` +
`journal` works natively (old `RR_JOURNAL[pid]` KeyError'd for new ids → now
`RR_JOURNAL.get(pid) or e.get("journal")`). Reconciled by coverage: all 393 ids covered
once, no dupes/gaps. New totals: **393 papers → 211 published / 27 forthcoming / 59 R&R /
94 working / 2 not found.**

**Dashboard generalized to N conferences.** Replaced the hardcoded NBER/Utah pairing with a
data-driven `CONF_META`/`CONF_ORDER` (known confs get a short label + chip color + fixed
left→right order; unknown confs still render, appended, gray chip). Both cohort charts now
lay out one bar per conference present each year, with per-year tick centering over the
*actual* bars (the old `confs.length` centering broke with sparse coverage). Conference filter
dropdown + list chips are data-driven, so a 5th conference needs no dashboard edit. Verified in
browser: 4-conf status chart, journal chart, filter, hover tooltip, R&R toggle all correct.

**Overlap note.** Many papers recur across these IO venues (e.g. "Energy Transitions in
Regulated Markets" = iosp2024-01 & utah2024-02, both forthcoming AER; "What Do News Readers
Want?" = iosp2025-08 & utah2025-07, both WP) — each appearance is its own row, and reuse +
consistent lookups keep them in agreement.

## 2026-07-13 — Cowles backfill, attribution audit, and comparison mode

**Cowles correction.** The earlier claim that Models & Measurement began in 2025 was caused
by probing only the newest URL pattern. The Cowles archive links four older agendas under
three different path families. Recovered **42 papers**: 12 in 2021 and 10 in each of
2022–2024. With 2025–2026, Cowles now has **62 papers across 2021–2026**. Batch 29 contains
the outcomes for all 42 additions: 15 published/accepted, 10 R&R, and 17 working papers.

**Three-state taxonomy.** `build_dashboard.py` now normalizes accepted/forthcoming records to
`published` and uncirculated/not-found records to `working_paper`. The enriched outputs use
exactly three statuses: **253 published / 69 R&R / 113 working paper** across 435 conference
appearances. Issue year and lag remain null for accepted papers not yet assigned to an issue.

**Attribution audit.** Audited all 393 pre-backfill records for source coverage, required
metadata, lag consistency, duplicates/cross-listings, and stale-prone R&Rs. All 297 placed
records had a URL and evidence note; no genuine publication-attribution correction was found.
`data/AUDIT_REPORT.md` contains the coverage manifest and checks. The 29 entries in
`data/audit_corrections.json` document taxonomy-only changes (27 forthcoming → published,
2 not-found → working paper).

**Comparison mode.** Selecting one conference enables a second conference selector. With two
selected, dashboard summaries, filters, cohort charts, and the paper list are restricted to
years present in both series. Paired conference bars and two summary boxes show the three
status shares side by side.

## 2026-07-14 — FTC Micro + Northwestern Antitrust

**FTC Microeconomics Conference.** Followed the official FTC archive and yearly event pages,
then extracted the academic paper sessions from the official agenda PDFs. Included 18 editions:
2008–2024 annually plus 2026 (the conference skipped 2025), yielding **177 paper appearances**.
Excluded registration, welcomes, keynotes, panels, discussants, and the 2026 policy-and-research
session. Source hub: `https://www.ftc.gov/microeconomics`.

**Northwestern Antitrust Economics and Competition Policy.** Parsed the paper lists and linked
agendas on the current and past-conference pages. Recovered **113 paper appearances** across
2011–2019 and 2021–2025. The series itself began in 2008 and did not meet in 2020, but the live
archive preserves only event-level references—not recoverable paper programs—for 2008–2010,
so those editions remain an explicit coverage gap rather than being reconstructed from secondary
mentions. Sources: `https://www.law.northwestern.edu/research-faculty/clbe/events/antitrust/`
and `https://www.law.northwestern.edu/research-faculty/clbe/events/antitrust/past.html/`.

**Publication outcomes.** Reused verified outcomes for cross-listed papers, matched older
publications against journal/Crossref metadata, and conservatively left unmatched papers as
working papers. Recent R&Rs were checked against author CVs/pages and require a named target
journal; accepted, conditionally accepted, and forthcoming papers are normalized to `published`.
Batch 30 contains all **290** new outcomes: **148 published/accepted, 14 R&R, 128 working**.
After reconciliation, the full dashboard contains **725 appearances: 401 published, 82 R&R,
242 working paper**. One older record that reported an unnamed R&R was conservatively returned
to working-paper status under the named-journal rule.

## 2026-07-14 — author-CV audit of every remaining working paper

Rechecked all **242 rows / 232 distinct titles** that were neither published nor assigned to a
named-journal R&R. The 114 pre-FTC/Northwestern rows already had a July 2026 author-page pass;
the 128 FTC/Northwestern rows received the same treatment, with exact-title and publisher
checks used to follow title changes. Rules stayed conservative: "under review" is not R&R,
an unnamed R&R stays `working_paper`, and accepted/conditionally accepted/forthcoming is
`published`.

The fresh pass corrected **57** records: **52** have a journal publication or acceptance and
**5** have a named-journal R&R. The five R&Rs are `ftc2015-05` (AEJ: Microeconomics),
`ftc2023-06` (JPE), `ftc2024-01` (IJIO), `ftc2024-02` (Econometrica), and `nwae2024-03`
(AER). The rebuilt totals are **453 published/accepted, 87 R&R, and 185 working papers**.
The reviewed overrides are reproducible via `scripts/apply_batch30_cv_audit.py`; scope,
evidence rules, examples, and the full retained-working manifest are in
`data/WORKING_PAPER_CV_AUDIT.md`.

## 2026-07-14 — Cowles Structural Microeconomics, 2016–2019

Recovered complete two-day programs from official Cowles pages preserved by the Internet
Archive: 12 papers in each of 2016–2018 and 13 in 2019, for **49 appearances**. These are
the predecessor Structural Microeconomics series and are combined with Models & Measurement
under the existing `Cowles M&M` data key; the dashboard displays the fuller series name.

Batch 31 records the publication/CV audit: **33 published/accepted, 3 R&R, and 13 working
papers**. The live R&Rs are `cowles2017-12` (Review of Economic Studies), `cowles2019-01`
(second-round R&R, Review of Economic Studies), and `cowles2019-02` (Journal of Political
Economy). Retitled lineages were checked against matching authors, project descriptions, and
publisher metadata; notable examples include the 2019 trade paper becoming *Trade and
Domestic Distortions: The Case of Informality* (Econometrica 2026), and the 2018 kidney
assignment paper changing coauthors in its published version.

The rebuilt dataset has **774 appearances: 486 published/accepted, 90 R&R, and 198 working
papers**. Cowles now contributes 111 appearances across 2016–2019 and 2021–2026; 2020
remains a coverage gap.

## 2026-07-14 — comparison year windows

Conference comparisons can now be narrowed to a contiguous calendar window with `From` and
`Through` selectors. The controls appear only after two conferences are selected, offer only
years represented in both series, and constrain the comparison summaries, cohort charts,
lag/journal charts, year filter, and paper list together. Reversed endpoints are normalized to
a one-year window. The generated dashboard and all conference-pair/year-range invariants were
validated after rebuilding.

## 2026-07-14 — year-by-year comparison detail

Comparison mode now adds two explicit shared-year tables beneath the aggregate conference
summary: publication-status counts (published / R&R / working paper) and journal placements
with the placed-paper share and journal mix. Both follow the comparison window, individual
year selection, all other dashboard filters, and the existing option to include R&Rs at their
target journals.

The publication-status and journal-placement cards remain separate full-width rows. Within
each row, comparison mode renders one chart per selected conference and places those two charts
side by side on desktop, using a common vertical scale within the pair. They stack on narrow
screens. The detailed tables are collapsed by default and can be shown or hidden from the
comparison header without losing the selected conferences, year window, or filters.

The filter bar also exposes an all-data CSV download. It serializes the dashboard's embedded
774-row enriched dataset in the browser, including agenda and publication titles/authors,
three-state status, journal, issue year, lag, source URL, and evidence note; it does not depend
on a neighboring data file or server route.
