#!/usr/bin/env python3
"""Find possible renamed publication lineages for unresolved NBER SI papers.

This pass targets the failure mode where an agenda title disappeared but the
same author set later published or circulated the project under a revised title.
It generates candidates; it does not directly change dashboard status.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from build_dashboard import norm_journal
from audit_nber_si_scholar import parse_results as parse_scholar_results


ROOT = Path(__file__).resolve().parents[1]
ROWS_PATH = ROOT / "nber_si" / "data" / "papers_enriched.json"
CANDIDATES_PATH = ROOT / "nber_si" / "data" / "renamed_lineage_candidates.json"
CACHE = ROOT / "nber_si" / "cache" / "renamed_lineages"
SCHOLAR_CACHE = ROOT / "nber_si" / "cache" / "scholar"

NONPUBLICATION_VENUES = {
    "ssrn electronic journal",
    "finance and economics discussion series",
    "international finance discussion papers",
    "academy of management proceedings",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
    "how", "in", "is", "it", "its", "of", "on", "or", "the", "to", "under", "using",
    "with", "without", "what", "when", "where", "why",
}
TITLE_HISTORY_RE = re.compile(
    r"((?:previously|formerly|earlier|prior).{0,100}(?:circulated|titled|called|draft|version|title)"
    r"|(?:circulated|titled|called).{0,100}(?:previously|formerly|as|under))",
    re.I | re.S,
)


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(value)).strip()


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "").replace("\x00", " ")).strip()


def surnames_from_names(names: list[str]) -> set[str]:
    return {norm(name).split()[-1] for name in names if norm(name)}


def row_surnames(row: dict) -> set[str]:
    return surnames_from_names(row.get("authors_list") or [])


def crossref_surnames(item: dict) -> set[str]:
    return surnames_from_names([author.get("family") or "" for author in item.get("author", [])])


def distinctive_terms(title: str) -> list[str]:
    return [tok for tok in norm(title).split() if len(tok) >= 5 and tok not in STOPWORDS][:8]


def title_scores(old_title: str, new_title: str) -> tuple[float, float, list[str]]:
    old_norm, new_norm = norm(old_title), norm(new_title)
    ratio = SequenceMatcher(None, old_norm, new_norm).ratio()
    old_terms = set(distinctive_terms(old_title))
    new_terms = set(norm(new_title).split())
    overlap = sorted(old_terms & new_terms)
    coverage = len(overlap) / len(old_terms) if old_terms else 0.0
    return ratio, coverage, overlap


def publication_year(item: dict) -> int | None:
    for key in ("published-print", "published", "issued", "published-online"):
        parts = (item.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            return int(parts[0][0])
    return None


def is_publication(item: dict) -> bool:
    venue = norm(" ".join(item.get("container-title") or []))
    if not venue or venue in NONPUBLICATION_VENUES:
        return False
    return not any(term in venue for term in ("working paper", "working papers", "discussion paper", "discussion papers"))


def crossref_cache_path(query: str) -> Path:
    return CACHE / "crossref" / (hashlib.sha1(query.encode()).hexdigest() + ".json")


def query_crossref(row: dict, refresh: bool = False) -> dict:
    terms = distinctive_terms(row["title"])[:5]
    query = " ".join(terms)
    first_author = (row.get("authors_list") or [row.get("agenda_authors", "")])[0]
    params = {
        "query.author": first_author,
        "query.bibliographic": query,
        "rows": "12",
        "filter": "type:journal-article",
        "select": "DOI,title,container-title,published,issued,published-print,published-online,author,URL,type",
    }
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    path = crossref_cache_path(url)
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (academic research audit)"})
    last: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read())
            out = {"query_url": url, "items": payload.get("message", {}).get("items", [])}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, ensure_ascii=False))
            return out
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    return {"query_url": url, "items": [], "error": str(last)}


def pdf_cache_path(url: str) -> Path:
    return CACHE / "pdf_first_pages" / (hashlib.sha1(url.encode()).hexdigest() + ".txt")


def fetch_first_pages_text(url: str, refresh: bool = False) -> str:
    if not url or ".pdf" not in urllib.parse.urlparse(url).path.lower():
        return ""
    path = pdf_cache_path(url)
    if path.exists() and not refresh:
        return path.read_text(errors="replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (academic research audit)"})
        with urllib.request.urlopen(request, timeout=35) as response:
            payload = response.read(8_000_000)
        if not payload.startswith(b"%PDF"):
            return ""
        reader = PdfReader(BytesIO(payload))
        text = "\n".join((reader.pages[i].extract_text() or "") for i in range(min(3, len(reader.pages))))
        path.write_text(clean_text(text))
        return path.read_text(errors="replace")
    except Exception as exc:
        path.write_text(f"FETCH_ERROR {exc}")
        return ""


def title_history_notes(text: str, old_title: str, new_title: str) -> list[str]:
    if not text:
        return []
    notes = []
    old_key, new_key = norm(old_title), norm(new_title)
    for hit in TITLE_HISTORY_RE.finditer(text):
        context = clean_text(text[max(0, hit.start() - 120):hit.end() + 220])
        key = norm(context)
        old_terms = set(distinctive_terms(old_title))
        coverage = len(old_terms & set(key.split())) / len(old_terms) if old_terms else 0
        if old_key in key or coverage >= 0.6:
            notes.append(context[:500])
        elif new_key in key and re.search(r"previously|formerly|earlier|circulated|titled", key):
            notes.append(context[:500])
    return notes[:3]


def scholar_cache_path(query: str) -> Path:
    return SCHOLAR_CACHE / (hashlib.sha1(query.encode("utf-8")).hexdigest() + ".html")


def query_scholar(row: dict, candidate_title: str, refresh: bool = False) -> dict:
    query = f"{row['title']} {candidate_title} {(row.get('authors_list') or [''])[0]}"
    path = scholar_cache_path(query)
    if not path.exists() or refresh:
        url = "https://scholar.google.com/scholar?" + urllib.parse.urlencode({"hl": "en", "q": query})
        request = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(request, timeout=45) as response:
            page = response.read().decode("utf-8", "replace")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page)
    page = path.read_text(errors="replace")
    return {
        "query": query,
        "results": parse_scholar_results(page, row)[:5],
    }


def candidate_from_item(row: dict, item: dict) -> dict | None:
    old_surnames = row_surnames(row)
    new_surnames = crossref_surnames(item)
    if not old_surnames or old_surnames != new_surnames:
        return None
    year = publication_year(item)
    if year is None or year < int(row["year"]):
        return None
    if not is_publication(item):
        return None
    title = clean_text(" ".join(item.get("title") or []))
    if not title or norm(title) == norm(row["title"]):
        return None
    ratio, coverage, overlap = title_scores(row["title"], title)
    if ratio < 0.34 and coverage < 0.30:
        return None
    venue = norm_journal(clean_text(" ".join(item.get("container-title") or [])))
    url = item.get("URL") or ("https://doi.org/" + item["DOI"] if item.get("DOI") else None)
    return {
        "paper_id": row["id"],
        "agenda_title": clean_text(row["title"]),
        "candidate_title": title,
        "agenda_authors": clean_text(row.get("agenda_authors")),
        "program": row.get("program"),
        "conference_year": row.get("year"),
        "candidate_year": year,
        "journal": venue,
        "url": url,
        "doi": item.get("DOI"),
        "title_ratio": round(ratio, 3),
        "distinctive_term_coverage": round(coverage, 3),
        "distinctive_term_overlap": overlap,
        "author_surnames": sorted(old_surnames),
        "review_state": "needs_confirmation",
    }


def select_rows(rows: list[dict], limit: int | None, min_year: int, max_year: int | None, offset: int = 0) -> list[dict]:
    queue = [
        row for row in rows
        if row.get("status") == "working_paper"
        and row.get("verification") in {
            "provisional",
            "author_page_checked_no_named_status",
            "multiple_authors_cross_checked",
        }
        and int(row.get("year") or 0) >= min_year
        and (max_year is None or int(row.get("year") or 0) <= max_year)
    ]
    queue.sort(key=lambda row: (row["year"], row.get("program") or "", row["title"]))
    out, seen = [], set()
    for row in queue:
        key = norm(row["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if limit and len(out) >= limit:
            break
    return out[offset:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--min-year", type=int, default=2015)
    parser.add_argument("--max-year", type=int)
    parser.add_argument("--output", default=str(CANDIDATES_PATH))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--scholar", type=int, default=0, help="run Scholar checks for this many top candidates")
    parser.add_argument("--pdf", type=int, default=40, help="run PDF first-page checks for this many top candidates")
    args = parser.parse_args()

    rows = json.loads(ROWS_PATH.read_text())
    by_id = {row["id"]: row for row in rows}
    selected = select_rows(rows, None, args.min_year, args.max_year, args.offset)
    if args.limit:
        selected = selected[:args.limit]
    candidates: dict[tuple[str, str], dict] = {}
    for n, row in enumerate(selected, 1):
        result = query_crossref(row, args.refresh)
        for item in result.get("items", []):
            candidate = candidate_from_item(row, item)
            if candidate:
                candidates[(candidate["paper_id"], norm(candidate["candidate_title"]))] = candidate
        if n % 50 == 0:
            print(f"crossref {n}/{len(selected)}", flush=True)
    ranked = sorted(
        candidates.values(),
        key=lambda cand: (
            -cand["distinctive_term_coverage"],
            -cand["title_ratio"],
            cand["conference_year"],
            cand["agenda_title"],
        ),
    )
    for cand in ranked[:args.pdf]:
        row = by_id[cand["paper_id"]]
        notes = []
        notes.extend(title_history_notes(fetch_first_pages_text(row.get("paper_url"), args.refresh),
                                         row["title"], cand["candidate_title"]))
        notes.extend(title_history_notes(fetch_first_pages_text(cand.get("url"), args.refresh),
                                         row["title"], cand["candidate_title"]))
        if notes:
            cand["pdf_title_history_notes"] = notes
            cand["review_state"] = "strong_candidate_pdf_title_history_note"
    scholar_checked = 0
    for cand in ranked:
        if scholar_checked >= args.scholar:
            break
        if cand.get("review_state") == "strong_candidate_pdf_title_history_note" or cand["distinctive_term_coverage"] >= 0.5:
            try:
                cand["scholar_check"] = query_scholar(by_id[cand["paper_id"]], cand["candidate_title"], args.refresh)
                scholar_checked += 1
                time.sleep(3)
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                cand["scholar_error"] = str(exc)
                break
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(ranked, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "selected_titles": len(selected),
        "candidate_lineages": len(ranked),
        "pdf_checked": min(args.pdf, len(ranked)),
        "scholar_checked": scholar_checked,
        "with_pdf_title_history_notes": sum(bool(c.get("pdf_title_history_notes")) for c in ranked),
        "output": str(output_path.relative_to(ROOT) if output_path.is_relative_to(ROOT) else output_path),
    }, indent=2))


if __name__ == "__main__":
    main()
