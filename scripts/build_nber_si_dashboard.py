#!/usr/bin/env python3
"""Build the separate NBER Summer Institute program dashboard.

The project deliberately reuses the established dashboard renderer so comparison
behavior and metric definitions stay aligned with the conference dashboard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_FIELDS = {
    "id", "program", "conference", "meeting_title", "year", "date", "title", "agenda_authors",
    "authors", "status", "journal", "pub_year", "lag", "published_title", "url", "paper_url",
    "nber_working_paper", "verification", "evidence_source", "evidence_url", "evidence_authors",
    "evidence_urls", "note", "meeting_url",
}


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"dashboard template marker not found: {old[:80]!r}")
    return text.replace(old, new, 1)


def main() -> None:
    full_rows = json.loads((ROOT / "nber_si" / "data" / "papers_enriched.json").read_text())
    # Keep the self-contained page and its CSV download focused on reader-facing
    # fields; raw author-profile objects remain in the versioned JSON dataset.
    rows = [{key: value for key, value in row.items() if key in DASHBOARD_FIELDS}
            for row in full_rows]
    template = (ROOT / "dashboard" / "template.html").read_text()
    template = replace_once(template, "<title>Conference → Publication</title>",
                            "<title>NBER Summer Institute → Publication</title>")
    template = replace_once(template, "const AGGREGATE_ALL = false;", "const AGGREGATE_ALL = true;")

    row_count = f"{len(rows):,}"
    header = f"""<h1>NBER Summer Institute → Publication</h1>
  <p class="sub">Publication outcomes for research papers presented across <b>NBER Summer Institute programs</b>,
  2015–2026. Select one program or compare two side by side using their overlapping years. Published and
  forthcoming papers are combined; R&amp;Rs remain a separate status.</p>
  <div class="about-row">
    <span>Data snapshot: July 2026 · {row_count} paper appearances from official NBER agendas. Automated matches and pending CV checks are labeled in the data.</span>
    <a class="methodology-btn" href="https://github.com/shoshievass/conference-to-pub/tree/main/nber_si#methodology" target="_blank" rel="noopener">Methodology &amp; README</a>
    <a class="methodology-btn" href="../" rel="noopener">IO conference dashboard</a>
  </div>"""
    template, count = re.subn(r'<h1>Conference → Publication</h1>.*?</div>\s*\n\s*<div class="filters">',
                              header + '\n\n  <div class="filters">', template, count=1, flags=re.S)
    if count != 1:
        raise ValueError("could not replace dashboard header")

    template = template.replace('aria-label="Conference"><option value="">All conferences</option>',
                                'aria-label="NBER SI program"><option value="">All SI programs</option>')
    template = template.replace('aria-label="Compare with another conference"',
                                'aria-label="Compare with another SI program"')
    template = template.replace('Publication status by conference year', 'Publication status by SI year')
    template = template.replace('Journal placement by conference year', 'Journal placement by SI year')
    template = template.replace('Conference-to-print lag', 'SI-to-print lag')
    template = template.replace('from conference to print', 'from Summer Institute to print')
    template = template.replace('shared conference years', 'shared SI years')
    template = template.replace('conference-year cohort', 'SI program-year cohort')
    template = template.replace('papers presented', 'paper appearances')

    verification_select = """<select id="f-verification">
      <option value="">Any evidence level</option>
      <option value="multiple_authors_cross_checked">Multiple authors cross-checked</option>
      <option value="cross_checked_prior_research">Cross-checked against prior research</option>
      <option value="cross_checked_author_source">Cross-checked against an author source</option>
      <option value="author_page_checked_no_named_status">Author source checked — no named status</option>
      <option value="official_nber_published">Official NBER publication record</option>
      <option value="automated_crossref">Automated Crossref match</option>
      <option value="provisional">Provisional — author audit pending</option>
    </select>"""
    marker = '    <select id="f-journal"><option value="">Any journal</option></select>'
    template = replace_once(template, marker, '    ' + verification_select + '\n' + marker)

    evidence_guide = """<details class="caveats" style="margin-top:12px">
    <summary><b>What do the evidence levels mean?</b></summary>
    <p><b>Multiple authors cross-checked:</b> two or more distinct coauthors' CVs or research pages independently support the displayed classification. For a journal outcome, they report the same named-journal status; for a working paper, the exact title appears on multiple author sources without a named R&amp;R, acceptance, or forthcoming label.</p>
    <p><b>Cross-checked against prior research:</b> individually researched in the original conference-to-publication project using publication or author sources.</p>
    <p><b>Cross-checked against an author source:</b> one linked author's current CV or research page supports the named-journal status.</p>
    <p><b>Author source checked — no named status:</b> the exact title appears on one author's CV or page, but no named-journal R&amp;R, acceptance, or forthcoming label was found.</p>
    <p><b>Official NBER publication record:</b> the NBER working-paper page lists a published version.</p>
    <p><b>Automated Crossref match:</b> a high-confidence title-and-author journal match that has not necessarily received an individual source review.</p>
    <p><b>Provisional — author audit pending:</b> no reliable match has been found yet. This is uncertainty, not proof that the paper remains unpublished.</p>
  </details>"""
    template = replace_once(template, '  <div class="filters">', evidence_guide + '\n\n  <div class="filters">')

    caveat = """<div class="caveats">
    <b>Caveats.</b> This is a July 14, 2026 snapshot. Many 2026 meetings had not yet occurred;
    their posted agendas are included and recent cohorts are heavily right-censored. Agenda rows come from
    NBER's official Summer Institute schedules and conference API. Obvious meeting-title changes are joined
    into recurring program series, while substantively distinct workshops remain separate. Cross-checked
    outcomes inherited from the IO-conference project take precedence. Additional published matches use
    high-confidence Crossref journal metadata. Rows marked “Provisional — author audit pending” had no verified journal
    match in that pass and are provisionally shown as working papers; they must not be interpreted as a
    completed author-CV determination. Working-paper series are not journal publications, and an R&amp;R is
    not an acceptance.
  </div>"""
    template, count = re.subn(r'<div class="caveats">.*?</div>\s*</div>\s*<div class="tooltip"',
                              caveat + '\n</div>\n<div class="tooltip"', template, count=1, flags=re.S)
    if count != 1:
        raise ValueError("could not replace caveat")

    template, count = re.subn(r'const CONF_META = \{.*?\n\};', 'const CONF_META = {};', template, count=1, flags=re.S)
    if count != 1:
        raise ValueError("could not replace conference metadata")

    template = replace_once(
        template,
        'const conf = $("#f-conf").value, st = $("#f-status").value, j = $("#f-journal").value,\n        yr = $("#f-year").value, q = $("#f-q").value.trim().toLowerCase();',
        'const conf = $("#f-conf").value, st = $("#f-status").value, j = $("#f-journal").value,\n        ver = $("#f-verification").value, yr = $("#f-year").value, q = $("#f-q").value.trim().toLowerCase();')
    template = replace_once(template, '    (!j || p.journal === j) &&\n    (!yr || String(p.year) === yr) &&',
                            '    (!j || p.journal === j) &&\n    (!ver || p.verification === ver) &&\n    (!yr || String(p.year) === yr) &&')
    template = template.replace("All conferences</option>", "All SI programs</option>")
    template = template.replace('Choose a conference to compare…', 'Choose an SI program to compare…')
    template = template.replace('Compare side by side…', 'Compare SI programs…')
    template = replace_once(template, '["f-status", "f-journal", "f-year", "f-q"]',
                            '["f-status", "f-verification", "f-journal", "f-year", "f-q"]')
    template = replace_once(
        template,
        'const CSV_FIELDS = ["id", "conference", "year", "title", "agenda_authors", "status", "journal",\n  "pub_year", "lag", "published_title", "authors", "url", "note"];',
        'const CSV_FIELDS = ["id", "program", "meeting_title", "year", "date", "title", "agenda_authors",\n  "status", "journal", "pub_year", "lag", "published_title", "authors", "url", "paper_url",\n  "nber_working_paper", "verification", "evidence_source", "evidence_url", "evidence_authors", "evidence_urls", "note", "meeting_url"];')
    template = template.replace('conference-to-publication-data.csv', 'nber-si-to-publication-data.csv')
    template = replace_once(
        template,
        '  const placedLabel = `published (${pub.length})` + (rr.length ? ` · ${rr.length} R&R` : "");\n  $("#tiles").innerHTML = [',
        '  const placedLabel = `published (${pub.length})` + (rr.length ? ` · ${rr.length} R&R` : "");\n'
        '  const evidenced = rows.filter((p) => p.verification !== "provisional").length;\n'
        '  $("#tiles").innerHTML = [')
    template = replace_once(
        template,
        '    [jset.size, "distinct journals" + (rrCounts() ? " (incl. R&R)" : "")],',
        '    [jset.size, "distinct journals" + (rrCounts() ? " (incl. R&R)" : "")],\n'
        '    [pct(evidenced, rows.length), `${evidenced} rows with non-provisional evidence`],')
    template = template.replace('/*__DATA_JSON__*/[]', json.dumps(rows, separators=(",", ":"), ensure_ascii=False))

    outputs = [ROOT / "nber_si" / "dashboard" / "index.html", ROOT / "docs" / "nber-si" / "index.html"]
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
