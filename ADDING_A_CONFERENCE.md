# How to add a conference

This repo tracks where papers from several economics conferences ended up being
published. The pipeline is deliberately additive — every conference flows through the
same steps and the dashboard is data-driven, so adding one is mechanical. This doc is
the runbook.

## Pipeline recap

```
data/papers.json            one row per (paper, conference-year): {id, conference, year, title, agenda_authors}
      │
      ▼  (publication lookups, one JSON file per research batch)
data/lookups/batch-*.json   {id, status, journal, pub_year, published_title, authors, url, note}
      │
      ▼  scripts/build_dashboard.py   (merge + normalize journals + promote R&Rs)
data/papers_enriched.json / .csv      merged, normalized master
dashboard/index.html                  self-contained dashboard (template + data inlined)
```

`build_dashboard.py` globs **all** `batch-*.json`, so new conferences just add new batch
files and new `papers.json` rows. IDs use a per-conference prefix + `-NN` (e.g.
`iosp2025-03`, `cowles2026-01`). One paper presented at several conferences gets one row
per appearance; they resolve to the same outcome (reuse — see step 3).

Statuses: `published` (journal + `pub_year`), `forthcoming` (accepted, no issue yet),
`rr` (revise-and-resubmit at a named journal — **not** an acceptance), `working_paper`,
`not_found`.

---

## Step 1 — Scrape the agenda (all years)

Goal: a list of `{title, authors}` per year. Two site patterns seen so far:

### NBER program meetings (SI IO, IO Spring, …) — browser required
Plain `curl`/WebFetch get **403** (bot protection). Use the in-app browser:
1. Find the meeting's `conf_id` from the "Print agenda" link on any year's page
   (`conference.nber.org/agenda/simple_printable?conf_id=…`). Schemes seen:
   `SI{YY}IO` (Summer Institute IO), `IOs{YY}` (IO Spring program meeting).
2. Navigate the browser to that printable URL once (to be on the `conference.nber.org`
   origin), then `fetch()` every year same-origin from the page context. Parse the HTML:
   - paper title → `<em>…</em>` inside a `.agenda-entry` row that also has `.paper-authors`
   - authors → `class="author-name">…` within `.paper-authors` (discussants are a
     separate `.discussant-name` — exclude them)
   - strip control-char ligature artifacts (`Eff\x0bects` → `Effects`) and dedupe by title.

   The exact browser snippet used lives in `NOTEBOOK.md` (2026-07-13 entries) and can be
   pasted into `mcp__Claude_Browser__javascript_tool`.

### Cowles summer conferences — curl works
`curl -A '<browser UA>' 'https://cowles.yale.edu/conferences/<series>/<year>'` returns the
full page (agenda inline). The agenda is a Time/Title/Presented-by table inside
`<details class="layout__details">`. Two row formats appear:
- title in `<a>`/plain cell, presenter after `<span class="label">Speaker: </span>`
- title in `<h4>`, presenter in `<strong>Speaker: NAME (aff)</strong>` (trailing `*` = speaker)

A row is a paper iff it contains `Speaker:` (breaks/meals don't). Cowles lists only the
**presenter**; recover coauthors during lookup (like Utah). See the Python parser in
`NOTEBOOK.md`. Probe which years exist by requesting `/<series>/<YYYY>` (301 = no such year).

> Save the raw scrape to a scratch JSON (`[{conf_id, year, papers:[{title, authors|speaker}]}]`).

## Step 2 — Build `papers.json` rows + reuse known outcomes

1. Pick a **conference label** and **id prefix** (e.g. `"NBER IO Spring"` / `iosp`,
   `"Cowles M&M"` / `cowles`).
2. For each paper, emit `{id, conference, year, title, agenda_authors}` and **append** to
   `data/papers.json` (skip ids already present).
3. **Reuse:** normalize each title (lowercase, alphanumeric) and match against
   `papers_enriched.json`. On a match, copy that paper's outcome into a "reuse" batch file
   instead of re-researching — this keeps cross-listed papers consistent and saves lookups.
   Note the source id in the `note` (`[reused from <id> — same paper]`).
4. Everything unmatched goes to a "needs lookup" list, split into chunks of ~14.

## Step 3 — Publication lookups (parallel research agents)

Dispatch one general-purpose agent per chunk. Each agent reads its chunk file and, for
each paper, finds the most-advanced **verified** status, writing a `batch-N.json`. Prompt
essentials (see the batch-19…28 dispatch in the session transcript for the full text):
- Only real peer-reviewed journals count as `published`; NBER/SSRN/CEPR WPs do **not**.
- `forthcoming` = officially accepted/forthcoming/in-press; an R&R is **not** forthcoming.
- `rr` = revise-and-resubmit at a named journal. **R&R includes** "major/minor revision",
  "revision requested", "invited to revise", "reject and resubmit", 2nd-round R&R. Plain
  "under review"/"submitted" is **not** R&R.
- **Before finalizing any `working_paper`, check the authors' CVs / websites / Google
  Scholar** for an R&R or acceptance the search missed. (This is the step that historically
  catches the most misses.)
- Verify journal + year against a publisher page or author CV, not memory. Recover the full
  author list.
- Tell the agent to do the research **itself** and not spawn sub-agents (they otherwise
  sometimes try to orchestrate and write nothing).

Reconcile by **coverage**: confirm every id has exactly one result across the batch files;
re-run any gaps directly.

## Step 4 — (optional) dedicated CV recheck

If lookups were done under looser R&R rules, run a second pass over the resulting
`working_paper` rows only, checking each paper's authors' CVs for R&R/acceptance. Fold any
promotions into the batch files (or the `RR_JOURNAL`/`RR_NOTE` maps below).

## Step 5 — Register in the dashboard (usually nothing to do)

The dashboard is **data-driven**: any conference in the data renders automatically. For a
nicer short label + chip color and a fixed left-to-right order in the cohort charts, add an
entry to `CONF_META` in `dashboard/template.html`:

```js
const CONF_META = {
  "<Conference label>": { short: "<chip label>", color: "var(--forthcoming)" },
  …
};
```
Unlisted conferences still appear (appended, default gray chip). The conference filter,
both cohort charts, and the paper list all read `CONF_ORDER`/`confShort`/`confColor`.

## Step 6 — Build, verify, commit

```bash
python3 scripts/build_dashboard.py          # prints the status breakdown
open dashboard/index.html                   # eyeball it; hard-refresh (Cmd-Shift-R) if stale
```
The build script's `RR_JOURNAL` map promotes specific ids to `rr` with a target journal
(for old batches that stored R&Rs as `working_paper`); `RR_NOTE` overrides the displayed
note. New batches can instead just write `status:"rr"` + `journal` directly — the build
handles both. Commit `papers.json`, the new `batch-*.json`, the regenerated enriched data +
`index.html`, and update `README.md` / `NOTEBOOK.md`.
