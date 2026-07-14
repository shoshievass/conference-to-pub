#!/usr/bin/env python3
"""Add publication outcomes to the collected NBER SI agenda rows.

Evidence is applied in two layers:
1. Cross-checked matches already in ``data/papers_enriched.json``.
2. High-confidence title matches to Crossref journal-article records cached under
   ``nber_si/cache/crossref``.

Unmatched rows remain working papers but carry ``verification=provisional`` until
the author-CV/R&R audit is completed. This distinction is displayed prominently in
the separate dashboard and retained in downloads.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import difflib
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import html as html_lib
from collections import defaultdict
from pathlib import Path

from build_dashboard import norm_journal


ROOT = Path(__file__).resolve().parents[1]
TOP_STATUS = {"published": 2, "forthcoming": 2, "rr": 1, "working_paper": 0}


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_display_text(value: str | None) -> str:
    """Normalize external metadata before it reaches JSON, CSV, or the dashboard."""
    value = html_lib.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def distinct_author_evidence(evidence: list[dict]) -> list[dict]:
    """Deduplicate source hits by author, not URL."""
    out, seen = [], set()
    for item in evidence:
        author = re.sub(r"<[^>]+>", "", item.get("author") or "").strip()
        key = norm(author)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({**item, "author": author})
    return out


def title_score(left: str, right: str) -> tuple[float, float]:
    a, b = norm(left), norm(right)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    aa, bb = set(a.split()), set(b.split())
    jaccard = len(aa & bb) / len(aa | bb) if aa | bb else 0
    return ratio, jaccard


def crossref_path(title: str) -> Path:
    digest = hashlib.sha1(norm(title).encode()).hexdigest()
    return ROOT / "nber_si" / "cache" / "crossref" / f"{digest}.json"


def query_crossref(title: str, authors: list[str], refresh: bool = False) -> dict:
    path = crossref_path(title)
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    params = {
        "query.title": title,
        "rows": 5,
        "filter": "type:journal-article",
        "select": "DOI,title,container-title,published,issued,published-print,published-online,author,URL,type",
    }
    if authors:
        params["query.author"] = authors[0]
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (mailto:research@example.com)"})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read())
            result = {"query_url": url, "items": payload.get("message", {}).get("items", [])}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False))
            return result
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    return {"query_url": url, "items": [], "error": str(last_error)}


def nber_wp_path(number: str) -> Path:
    return ROOT / "nber_si" / "cache" / "nber_wp" / f"{number.lower()}.html"


def query_nber_wp(number: str, refresh: bool = False) -> str:
    path = nber_wp_path(number)
    if path.exists() and not refresh:
        return path.read_text(errors="replace")
    url = f"https://www.nber.org/papers/{number.lower()}"
    request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (research dataset)"})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                page = response.read().decode("utf-8", "replace")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(page)
            return page
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    return f"<!-- fetch error: {last_error} -->"


def nber_published_version(page: str) -> dict | None:
    marker = re.search(r">Published Versions</h2>(.*?)(?:</div>|</section>)", page, flags=re.I | re.S)
    if not marker:
        return None
    for paragraph in re.findall(r"<p[^>]*>(.*?)</p>", marker.group(1), flags=re.I | re.S):
        link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', paragraph, flags=re.I | re.S)
        if not link:
            continue
        before, after = paragraph[:link.start()], paragraph[link.end():]
        before_text = html_lib.unescape(re.sub(r"<[^>]+>", " ", before))
        tail = html_lib.unescape(re.sub(r"<[^>]+>", " ", after)).strip().lstrip('"”').strip()
        year_match = re.search(r"\b((?:19|20)\d{2})\b", before_text)
        if not year_match:
            year_match = re.search(r"\b((?:19|20)\d{2})\b", tail)
        if tail.casefold().startswith("citation courtesy of"):
            # Some RePEc-supplied records put the full citation inside the link;
            # the normal title/author Crossref layer parses these more reliably.
            continue
        comma_journals = [
            "The Journal of Law, Economics, and Organization",
            "Journal of Money, Credit and Banking",
        ]
        journal = next((name for name in comma_journals if tail.startswith(name)), tail.split(",", 1)[0].strip().rstrip("."))
        if journal.startswith("Demography "):
            journal = "Demography"
        if (not journal or re.search(r"\d{5,}", journal) or "press" in journal.casefold()
                or journal.casefold().startswith("in ") or journal == "Academy of Management Proceedings"):
            continue
        title = clean_display_text(link.group(2)).strip('"').rstrip(",")
        return {
            "status": "published",
            "journal": norm_journal(journal),
            "pub_year": int(year_match.group(1)) if year_match else None,
            "published_title": title,
            "url": html_lib.unescape(link.group(1)),
        }
    return None


def publication_year(item: dict) -> int | None:
    for key in ("published-print", "published", "issued", "published-online"):
        parts = (item.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            return int(parts[0][0])
    return None


def best_crossref(title: str, result: dict, agenda_authors: list[str]) -> tuple[dict | None, float]:
    best, best_score = None, 0.0
    agenda_surnames = {norm(name).split()[-1] for name in agenda_authors if norm(name)}
    for item in result.get("items", []):
        venue = html_lib.unescape(" ".join(item.get("container-title") or []))
        venue_key = norm(venue)
        nonpublication = (
            venue_key in {
                "ssrn electronic journal",
                "finance and economics discussion series",
                "international finance discussion papers",
                "academy of management proceedings",
            }
            or "working paper" in venue_key
            or "working papers" in venue_key
            or "discussion paper" in venue_key
            or "discussion papers" in venue_key
            or venue_key.startswith("research square")
        )
        if nonpublication:
            continue
        candidate_surnames = {norm(author.get("family")).split()[-1]
                              for author in item.get("author", []) if norm(author.get("family"))}
        if agenda_surnames and not (agenda_surnames & candidate_surnames):
            continue
        candidate = " ".join(item.get("title") or [])
        ratio, jaccard = title_score(title, candidate)
        score = max(ratio, jaccard)
        # Exact token sets tolerate punctuation/subtitle changes; fuzzy matches
        # otherwise need to be very close to avoid joining similarly named papers.
        accepted = (jaccard >= 0.94) or (ratio >= 0.92 and jaccard >= 0.82)
        if accepted and score > best_score:
            best, best_score = item, score
    return best, best_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lookup", action="store_true", help="query Crossref for uncached titles")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    agenda = json.loads((ROOT / "nber_si" / "data" / "papers.json").read_text())
    checked = json.loads((ROOT / "data" / "papers_enriched.json").read_text())
    audit_file = ROOT / "nber_si" / "data" / "cv_audit.json"
    cv_audit = {row["normalized_title"]: row for row in json.loads(audit_file.read_text())} if audit_file.exists() else {}
    no_status_file = ROOT / "nber_si" / "data" / "cv_no_status_checks.json"
    no_status_checks = {row["normalized_title"]: row for row in json.loads(no_status_file.read_text())} if no_status_file.exists() else {}
    old: dict[str, list[dict]] = defaultdict(list)
    for row in checked:
        for title in (row.get("title"), row.get("published_title")):
            if title:
                old[norm(title)].append(row)

    unique_queries: dict[str, tuple[str, list[str]]] = {}
    for row in agenda:
        key = norm(row["title"])
        if key not in old and (args.lookup or crossref_path(row["title"]).exists()):
            unique_queries.setdefault(key, (row["title"], row.get("authors_list") or []))

    results: dict[str, dict] = {}
    if unique_queries:
        print(f"Crossref candidates: {len(unique_queries)} unique titles")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(query_crossref, title, authors, args.refresh): key
                       for key, (title, authors) in unique_queries.items()}
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                results[futures[future]] = future.result()
                if n % 250 == 0:
                    print(f"  {n}/{len(futures)}")

    wp_numbers = sorted({row["nber_working_paper"].lower() for row in agenda if row.get("nber_working_paper")})
    wp_pages: dict[str, str] = {}
    if wp_numbers:
        to_read = [n for n in wp_numbers if args.lookup or nber_wp_path(n).exists()]
        print(f"NBER working-paper pages: {len(to_read)}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(query_nber_wp, number, args.refresh): number for number in to_read}
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                wp_pages[futures[future]] = future.result()
                if n % 250 == 0:
                    print(f"  {n}/{len(futures)}")

    enriched = []
    stats = defaultdict(int)
    for row in agenda:
        out = dict(row)
        choices = old.get(norm(row["title"]), [])
        if choices:
            source = max(choices, key=lambda x: TOP_STATUS.get(x.get("status"), 0))
            for field in ("status", "journal", "pub_year", "published_title", "url", "note"):
                out[field] = source.get(field)
            out["verification"] = "cross_checked_prior_research"
            out["evidence_source"] = "existing conference-to-pub research"
            stats["cross_checked_prior_research"] += 1
        else:
            official = nber_published_version(wp_pages.get((row.get("nber_working_paper") or "").lower(), ""))
            candidate, score = best_crossref(row["title"], results.get(norm(row["title"]), {}), row.get("authors_list") or [])
            if official:
                out.update(official)
                out.update({
                    "note": "Published-version metadata from the official NBER working-paper page; final spot audit pending.",
                    "verification": "official_nber_published",
                    "evidence_source": "official NBER Published Versions record",
                })
                stats["official_nber_published"] += 1
            elif candidate:
                out.update({
                    "status": "published",
                    "journal": norm_journal(html_lib.unescape((candidate.get("container-title") or [None])[0])),
                    "pub_year": publication_year(candidate),
                    "published_title": clean_display_text(" ".join(candidate.get("title") or [])),
                    "url": candidate.get("URL") or ("https://doi.org/" + candidate["DOI"] if candidate.get("DOI") else None),
                    "note": f"High-confidence Crossref title match (score {score:.3f}); journal record requires spot audit.",
                    "verification": "automated_crossref",
                    "evidence_source": "Crossref journal-article metadata",
                })
                stats["automated_crossref"] += 1
            else:
                out.update({
                    "status": "working_paper",
                    "journal": None,
                    "pub_year": None,
                    "published_title": None,
                    "url": row.get("paper_url"),
                    "note": "No high-confidence journal match in the automated pass; author-CV/R&R audit pending.",
                    "verification": "provisional",
                    "evidence_source": "no verified journal match",
                })
                stats["provisional"] += 1
        audit = cv_audit.get(norm(row["title"]))
        if audit:
            audit_evidence = distinct_author_evidence(audit.get("evidence") or [{
                "author": audit["evidence_author"],
                "evidence_url": audit["evidence_url"],
                "status_phrase": audit["evidence_phrase"],
            }])
            multiple_authors = len(audit_evidence) >= 2
            out.update({
                "status": audit["status"],
                "journal": audit["journal"],
                "pub_year": audit.get("pub_year"),
                "verification": "multiple_authors_cross_checked" if multiple_authors else "cross_checked_author_source",
                "evidence_source": "author pages/CVs: " + ", ".join(x["author"] for x in audit_evidence),
                "evidence_url": audit["evidence_url"],
                "evidence_authors": [x["author"] for x in audit_evidence],
                "evidence_urls": [x["evidence_url"] for x in audit_evidence],
                "note": (f"{audit['evidence_phrase']} at {audit['journal']} cross-checked on "
                         f"{len(audit_evidence)} authors' pages/CVs in July 2026."
                         if multiple_authors else
                         f"{audit['evidence_phrase']} at {audit['journal']} per {audit_evidence[0]['author']}'s author page; cross-checked July 2026."),
            })
        elif out.get("verification") == "provisional" and norm(row["title"]) in no_status_checks:
            check = no_status_checks[norm(row["title"])]
            checked_evidence = distinct_author_evidence(check["evidence"])
            evidence = checked_evidence[0]
            multiple_authors = len(checked_evidence) >= 2
            out.update({
                "verification": "multiple_authors_cross_checked" if multiple_authors else "author_page_checked_no_named_status",
                "evidence_source": "author pages/CVs exact-title check: " + ", ".join(x["author"] for x in checked_evidence),
                "evidence_url": evidence["evidence_url"],
                "evidence_authors": [x["author"] for x in checked_evidence],
                "evidence_urls": [x["evidence_url"] for x in checked_evidence],
                "note": (f"Exact title cross-checked on {len(checked_evidence)} authors' pages/CVs; no named-journal R&R, "
                         "acceptance, or forthcoming phrase was detected with the project. Checked July 2026."
                         if multiple_authors else
                         "Exact title found on a linked author page/CV; no named-journal R&R, acceptance, or forthcoming phrase was detected with the project. Checked July 2026."),
            })
        out["conference"] = out["program"]  # reuse the established dashboard renderer
        out["authors"] = out.get("agenda_authors")
        out["lag"] = out["pub_year"] - out["year"] if out.get("pub_year") else None
        enriched.append(out)

    stats = defaultdict(int)
    for row in enriched:
        stats[row["verification"]] += 1

    data_dir = ROOT / "nber_si" / "data"
    (data_dir / "papers_enriched.json").write_text(json.dumps(enriched, indent=1, ensure_ascii=False) + "\n")
    fields = ["id", "program", "meeting_title", "year", "date", "title", "agenda_authors", "status",
              "journal", "pub_year", "lag", "published_title", "url", "paper_url", "nber_working_paper",
              "verification", "evidence_source", "evidence_url", "evidence_authors", "evidence_urls",
              "note", "meeting_url"]
    with (data_dir / "papers_enriched.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in enriched:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                             for key, value in row.items()})
    print(json.dumps({"rows": len(enriched), **stats}, indent=2))


if __name__ == "__main__":
    main()
