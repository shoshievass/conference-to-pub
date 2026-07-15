#!/usr/bin/env python3
"""Use Google Scholar as a conservative discovery layer for unresolved SI rows.

Scholar is not used as final status evidence: it mixes working-paper versions,
citations, and publication records. This script records candidate leads for
titles that are still unresolved, so any promotion can be independently checked
against an NBER, publisher, DOI, or author source.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
ROWS_PATH = ROOT / "nber_si" / "data" / "papers_enriched.json"
OUT_PATH = ROOT / "nber_si" / "data" / "scholar_audit_candidates.json"
PROVIDER_PATH = ROOT / "nber_si" / "data" / "scholar_provider_status.json"
CACHE_DIR = ROOT / "nber_si" / "cache" / "scholar"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "the", "to", "under", "using", "with",
}


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_text(value: str | None) -> str:
    return re.sub(r"[\x00-\x1f]+", " ", html.unescape(value or "")).strip()


def title_score(left: str, right: str) -> tuple[float, float]:
    a, b = norm(left), norm(right)
    ratio = SequenceMatcher(None, a, b).ratio()
    aa, bb = set(a.split()), set(b.split())
    jaccard = len(aa & bb) / len(aa | bb) if aa | bb else 0.0
    return ratio, jaccard


def surnames(row: dict) -> set[str]:
    return {norm(author).split()[-1] for author in row.get("authors_list") or [] if norm(author)}


def distinctive_terms(title: str) -> list[str]:
    terms = [tok for tok in norm(title).split() if len(tok) >= 5 and tok not in STOPWORDS]
    return sorted(set(terms), key=lambda tok: (-len(tok), tok))[:6]


def query_for(row: dict) -> str:
    names = row.get("authors_list") or []
    first = names[0] if names else row.get("agenda_authors", "").split(",")[0]
    pieces = [clean_text(row["title"]), clean_text(first)]
    return " ".join(piece for piece in pieces if piece)


def cache_path(query: str) -> Path:
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.html"


def fetch_scholar(query: str, refresh: bool = False) -> tuple[str, bool]:
    path = cache_path(query)
    if path.exists() and not refresh:
        return path.read_text(errors="replace"), True
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
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(page)
    return page, False


def parse_results(page: str, row: dict) -> list[dict]:
    if re.search(r"unusual traffic|sorry/index|captcha", page, re.I):
        raise RuntimeError("Google Scholar returned a traffic/CAPTCHA page")
    soup = BeautifulSoup(page, "html.parser")
    target_surnames = surnames(row)
    target_terms = set(distinctive_terms(row["title"]))
    parsed: list[dict] = []
    for rank, result in enumerate(soup.select(".gs_r.gs_or.gs_scl"), 1):
        heading = result.select_one(".gs_rt")
        if not heading:
            continue
        link = heading.find("a")
        title = clean_text(heading.get_text(" ", strip=True))
        title = re.sub(r"^\[[A-Z]+\]\s*", "", title).strip()
        url = link.get("href") if link else None
        meta = clean_text(result.select_one(".gs_a").get_text(" ", strip=True)) if result.select_one(".gs_a") else ""
        snippet = clean_text(result.select_one(".gs_rs").get_text(" ", strip=True)) if result.select_one(".gs_rs") else ""
        ratio, jaccard = title_score(row["title"], title)
        candidate_surnames = set(norm(meta).split())
        surname_overlap = sorted(target_surnames & candidate_surnames)
        term_overlap = sorted(target_terms & set(norm(title + " " + snippet).split()))
        parsed.append({
            "rank": rank,
            "title": title,
            "url": url,
            "meta": meta,
            "title_ratio": round(ratio, 3),
            "title_jaccard": round(jaccard, 3),
            "surname_overlap": surname_overlap,
            "distinctive_term_overlap": term_overlap,
            "candidate_kind": classify_candidate(url, meta),
        })
    return parsed


def classify_candidate(url: str | None, meta: str) -> str:
    text = norm(" ".join([url or "", meta]))
    if "doi org" in text or "aeaweb org" in text or "econometricsociety org" in text:
        return "possible_publisher_record"
    if "nber org" in text:
        return "possible_nber_record"
    if any(term in text for term in ("journal", "review", "econometrica", "quarterly", "american economic")):
        return "possible_journal_record"
    return "scholar_lead"


def audit_rows(rows: list[dict], limit: int | None, title_filter: str | None,
               completed_titles: set[str] | None = None) -> list[dict]:
    unresolved = [row for row in rows if row.get("status") == "working_paper"]
    if title_filter:
        title_key = norm(title_filter)
        unresolved = [row for row in unresolved if title_key in norm(row["title"])]
    # Older rows have had longer to publish and are more likely to reveal missed
    # renamed lineages, so they are the best first pass.
    unresolved.sort(key=lambda row: (row.get("year") or 9999, row.get("program") or "", row["title"]))
    seen = set()
    out = []
    for row in unresolved:
        key = norm(row["title"])
        if key in seen or key in (completed_titles or set()):
            continue
        seen.add(key)
        out.append(row)
        if limit and len(out) >= limit:
            break
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25,
                        help="unique unresolved titles to query; 0 means all remaining titles")
    parser.add_argument("--title", help="restrict to titles containing this text")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between uncached Scholar requests")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()

    rows = json.loads(ROWS_PATH.read_text())
    existing = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else []
    by_title = {norm(item["agenda_title"]): item for item in existing}
    completed_titles = {
        key for key, item in by_title.items()
        if not item.get("error") or not args.retry_errors
    }
    selected = audit_rows(rows, args.limit or None, args.title, completed_titles)
    fetched = cached = 0
    provider_block = None
    for n, row in enumerate(selected, 1):
        query = query_for(row)
        try:
            page, was_cached = fetch_scholar(query, args.refresh)
            if was_cached:
                cached += 1
            else:
                fetched += 1
            results = parse_results(page, row)[:5]
            by_title[norm(row["title"])] = {
                "agenda_title": clean_text(row["title"]),
                "program": row.get("program"),
                "year": row.get("year"),
                "agenda_authors": clean_text(row.get("agenda_authors")),
                "query": query,
                "queried_at": "2026-07-14",
                "results": results,
            }
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            by_title[norm(row["title"])] = {
                "agenda_title": clean_text(row["title"]),
                "program": row.get("program"),
                "year": row.get("year"),
                "agenda_authors": clean_text(row.get("agenda_authors")),
                "query": query,
                "queried_at": "2026-07-14",
                "error": str(exc),
            }
            print(f"blocked/error at {n}/{len(selected)}: {exc}")
            text = str(exc)
            provider_wide = isinstance(exc, RuntimeError) or any(
                marker in text.casefold() for marker in ("http error 403", "http error 429", "captcha", "unusual traffic")
            )
            if provider_wide:
                provider_block = {
                    "state": "exhausted_unavailable",
                    "provider": "Google Scholar",
                    "reason": text,
                    "attempted_in_probe": n,
                    "checked_at": "2026-07-14",
                    "note": "Provider-wide blocking applies to the remaining queue; Scholar snippets are discovery-only.",
                }
                break
            continue
        print(f"{n}/{len(selected)} {row['year']} {row['title'][:70]}")
        if n < len(selected) and not was_cached:
            time.sleep(args.delay + random.uniform(0, 1.25))
    OUT_PATH.write_text(json.dumps(sorted(by_title.values(), key=lambda item: (item.get("year") or 9999, item["agenda_title"])),
                                   indent=2, ensure_ascii=False) + "\n")
    if provider_block:
        PROVIDER_PATH.write_text(json.dumps(provider_block, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"selected": len(selected), "cached": cached, "fetched": fetched, "stored": len(by_title)}, indent=2))


if __name__ == "__main__":
    main()
