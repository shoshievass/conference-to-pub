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
