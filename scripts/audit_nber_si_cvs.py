#!/usr/bin/env python3
"""Build and apply the author-CV audit for provisional NBER SI papers.

Phase 1 discovers current author-controlled/institutional pages from official NBER
profiles. Network responses are cached. Later phases download likely CV/research
pages, match agenda projects, and record only explicit publication or named-journal
R&R evidence in ``nber_si/data/cv_audit.json``.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

from build_dashboard import JOURNAL_MAP, norm_journal


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "nber_si" / "cache" / "cv_audit"


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, re.sub(r"\s+", " ", html.unescape("".join(self.text))).strip()))
            self.href, self.text = None, []


def cache_path(kind: str, url: str, suffix: str = ".html") -> Path:
    return CACHE / kind / (hashlib.sha1(url.encode()).hexdigest() + suffix)


def cache_key_path(kind: str, key: str, suffix: str = ".html") -> Path:
    return CACHE / kind / (hashlib.sha1(key.encode()).hexdigest() + suffix)


def fetch(url: str, kind: str, refresh: bool = False) -> str:
    path = cache_path(kind, url)
    if path.exists() and not refresh:
        cached = path.read_text(errors="replace")
        if "FETCH_ERROR" not in cached:
            return cached
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (academic research audit)"})
    last: Exception | None = None
    attempts = 3 if kind == "nber_profiles" else 1
    timeout = 35 if kind == "nber_profiles" else 15
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
            text = payload.decode("utf-8", "replace")
            path.write_text(text)
            return text
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            last = exc
            time.sleep(attempt + 1)
    path.write_text(f"<!-- FETCH_ERROR {html.escape(str(last))} -->")
    return path.read_text()


def direct_document_url(url: str) -> str:
    drive = re.search(r"drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]+)", url)
    if drive:
        return f"https://drive.google.com/uc?export=download&id={drive.group(1)}"
    if "dropbox.com" in url:
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parts.query)
        query["dl"] = ["1"]
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query, doseq=True), ""))
    return url.strip()


def fetch_document(url: str, refresh: bool = False) -> str:
    url = direct_document_url(url)
    binary = cache_path("documents", url, ".bin")
    text_path = cache_path("document_text", url, ".txt")
    if text_path.exists() and not refresh:
        cached = text_path.read_text(errors="replace")
        if "FETCH_ERROR" not in cached:
            return cached
    binary.parent.mkdir(parents=True, exist_ok=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (academic research audit)"})
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read(15_000_000)
        binary.write_bytes(payload)
        if payload.startswith(b"%PDF"):
            subprocess.run(["pdftotext", "-layout", str(binary), str(text_path)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        else:
            text_path.write_text(visible_text(payload.decode("utf-8", "replace")))
    except Exception as exc:
        text_path.write_text(f"FETCH_ERROR {exc}")
    return text_path.read_text(errors="replace")


def external_links(page: str) -> list[dict]:
    parser = Links()
    parser.feed(page)
    out, seen = [], set()
    blocked_hosts = {"www.nber.org", "nber.org", "twitter.com", "x.com", "linkedin.com", "www.linkedin.com",
                     "scholar.google.com", "ideas.repec.org", "orcid.org", "www.youtube.com",
                     "bsky.app", "www.threads.net", "threads.net", "www.facebook.com", "facebook.com"}
    for href, text in parser.links:
        if not href.startswith(("http://", "https://")):
            continue
        host = urllib.parse.urlparse(href).netloc.lower()
        if host in blocked_hosts or href in seen:
            continue
        seen.add(href)
        out.append({"url": href, "text": text})
    return out


def visible_text(page: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page))).strip()


def clean_search_url(href: str) -> str:
    href = html.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
        href = urllib.parse.unquote(target)
    return href


def is_blocked_source_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.lower()
    blocked_hosts = {
        "nber.org", "twitter.com", "x.com", "linkedin.com", "scholar.google.com",
        "ideas.repec.org", "orcid.org", "youtube.com", "bsky.app", "threads.net",
        "facebook.com", "happenstance.ai", "askai.glarity.app",
    }
    if host in blocked_hosts:
        return True
    if any(host.endswith("." + blocked) for blocked in blocked_hosts):
        return True
    if "google.com/search" in host + path or "webcache" in path:
        return True
    return False


def search_duckduckgo(
    query: str,
    refresh: bool = False,
    max_results: int = 8,
    timeout: int = 8,
    cache_only: bool = False,
) -> list[dict]:
    path = cache_key_path("search", "ddg:" + query)
    page = None
    if path.exists() and not refresh:
        page = path.read_text(errors="replace")
        # A cached network failure is an unfinished attempt, not an empty
        # successful search. Retry it on the next recursive pass.
        if "FETCH_ERROR" in page:
            page = None
    elif cache_only:
        return []
    if page is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query})
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 conference-to-pub author-source audit"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                page = response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            page = f"<!-- FETCH_ERROR {html.escape(str(exc))} -->"
        path.write_text(page)
        time.sleep(0.35)
    results = []
    pattern = re.compile(r"<a\s+rel=\"nofollow\"\s+href=\"([^\"]+)\"\s+class=['\"]result-link['\"]>(.*?)</a>", re.S)
    for hit in pattern.finditer(page):
        url = clean_search_url(hit.group(1))
        if not url.startswith(("http://", "https://")) or is_blocked_source_url(url):
            continue
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", hit.group(2)))).strip()
        results.append({"url": url, "text": title, "source": "duckduckgo_lite", "query": query})
        if len(results) >= max_results:
            break
    return results


def discover_web_pages(author_name: str, refresh: bool = False, timeout: int = 8) -> list[dict]:
    if not author_name:
        return []
    queries = [
        f'"{author_name}" economist homepage research',
        f'"{author_name}" economics CV research',
    ]
    pages, seen = [], set()
    for query in queries:
        for result in search_duckduckgo(query, refresh=refresh, max_results=6, timeout=timeout):
            key = result["url"].rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            pages.append(result)
    return pages


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(value).lower()).strip()


def match_norm(value: str) -> str:
    value = html.unescape(value or "").translate(str.maketrans({
        "’": "'", "‘": "'", "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    })).replace("&", " and ")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    tokens = re.sub(r"[^a-z0-9]+", " ", value).strip().split()
    out, i = [], 0
    while i < len(tokens):
        if len(tokens[i]) == 1 and tokens[i].isalpha():
            j = i
            while j < len(tokens) and len(tokens[j]) == 1 and tokens[j].isalpha():
                j += 1
            if j - i >= 2:
                out.append("".join(tokens[i:j]))
                i = j
                continue
        out.append(tokens[i])
        i += 1
    return " ".join(out)


def likely_documents(page: str, base_url: str) -> list[dict]:
    parser = Links()
    parser.feed(page)
    out, seen = [], set()
    for href, text in parser.links:
        if not href or href.startswith(("mailto:", "javascript:", "#")):
            continue
        url = urllib.parse.urljoin(base_url, href)
        clue = norm(url + " " + text)
        if not re.search(r"\b(cv|vita|vitae|curriculum|research|publications?|working papers?)\b", clue):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "text": text, "is_pdf": ".pdf" in urllib.parse.urlparse(url).path.lower()})
    return out


STATUS_RE = re.compile(
    r"\b(r r|revise and resubmit|revise resubmit|major revision|revision requested|reject and resubmit|reject resubmit|forthcoming|conditionally accepted|accepted)\b",
    re.I,
)


def journal_near_status(context: str, status_start: int, status_end: int) -> str | None:
    key = norm(context)
    raw_matches = []
    center = (status_start + status_end) / 2
    aliases = sorted(JOURNAL_MAP, key=len, reverse=True)
    for alias in aliases:
        for hit in re.finditer(r"\b" + re.escape(norm(alias)) + r"\b", key):
            distance = abs(((hit.start() + hit.end()) / 2) - center)
            raw_matches.append((hit.start(), hit.end(), distance, len(norm(alias)), norm_journal(alias)))
    # Suppress short aliases embedded in a longer journal name (for example,
    # ``AER`` inside ``AER Insights``) before comparing distance to the status.
    matches = [
        (distance, -length, journal)
        for start, end, distance, length, journal in raw_matches
        if not any(
            other_start <= start and other_end >= end and other_length > length
            for other_start, other_end, _, other_length, _ in raw_matches
        )
    ]
    return min(matches)[2] if matches else None


def evidence_on_normalized(normalized: str, page_url: str, paper: dict,
                           sibling_titles: list[str]) -> dict | None:
    title = match_norm(paper["title"])
    if len(title.split()) < 4:
        return None
    pos = normalized.find(title)
    if pos < 0:
        return None
    after = normalized[pos + len(title):pos + len(title) + 360]
    hit = STATUS_RE.search(after)
    if not hit or hit.start() > 260:
        return None
    before_status = after[:hit.start()]
    tokens_between = len(before_status.split())
    for sibling in sibling_titles:
        sibling = match_norm(sibling)
        if sibling != title and len(sibling.split()) >= 4 and sibling in before_status:
            return None
    term = hit.group(1).lower()
    status = "rr" if term in {"r r", "revise and resubmit", "revise resubmit", "major revision", "revision requested", "reject and resubmit", "reject resubmit"} else "published"
    journal = journal_near_status(after, hit.start(), hit.end())
    # R&R evidence must name its journal. Forthcoming/accepted candidates also
    # require a journal before they can change dashboard status.
    if not journal:
        return None
    return {
        "paper_id": paper["id"],
        "title": paper["title"],
        "candidate_status": status,
        "journal": journal,
        "status_phrase": term,
        "evidence_url": page_url,
        "context": normalized[max(0, pos - 60):pos + len(title) + 420],
        "tokens_between_title_and_status": tokens_between,
        "local_title_ratio": 1.0,
        "distinctive_term_coverage": 1.0,
        "discovery": "exact-title author-source lineage",
        "review_state": "needs_human_confirmation",
    }


def evidence_on_page(page: str, page_url: str, paper: dict, sibling_titles: list[str]) -> dict | None:
    return evidence_on_normalized(match_norm(visible_text(page)), page_url, paper, sibling_titles)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--min-year", type=int, default=2015)
    parser.add_argument("--external", action="store_true", help="also inspect linked author pages and discover CVs")
    parser.add_argument("--documents", action="store_true", help="download strong CV/vita candidates and scan their text")
    parser.add_argument("--web-search", action="store_true", help="discover additional author pages from cached web search")
    parser.add_argument("--web-search-limit", type=int, default=500,
                        help="maximum authors to web-search in this pass; 0 means no limit")
    parser.add_argument("--web-search-offset", type=int, default=0,
                        help="number of sorted web-search authors to skip before applying the limit")
    parser.add_argument("--web-search-all", action="store_true",
                        help="web-search authors even when their NBER profile already exposes an external page")
    parser.add_argument("--web-search-only-unattempted", action="store_true",
                        help="skip authors whose web discovery is already terminal")
    parser.add_argument("--web-search-workers", type=int, default=4,
                        help="bounded parallel author discovery workers")
    parser.add_argument("--web-search-timeout", type=int, default=5,
                        help="timeout per author-discovery query")
    parser.add_argument("--reuse-sources", action="store_true",
                        help="start from cached cv_audit_sources.json instead of refetching all NBER profiles")
    parser.add_argument("--skip-profile-retries", action="store_true",
                        help="reuse profile records as-is while running bounded web-search tranches")
    args = parser.parse_args()

    papers = json.loads((ROOT / "nber_si" / "data" / "papers_enriched.json").read_text())
    # Audit every unresolved working-paper row. Restricting this queue to the
    # provisional evidence label excluded rows inherited from prior research
    # and rows whose exact title had appeared on one or more author pages.
    queue = [p for p in papers if p.get("status") == "working_paper"
             and p["year"] >= args.min_year]
    authors: dict[str, dict] = {}
    author_papers: dict[str, set[str]] = defaultdict(set)
    for paper in queue:
        for author in paper.get("author_profiles", []):
            url = author.get("nber_url")
            if url and url.startswith("/"):
                url = "https://www.nber.org" + url
            source_id = url or "missing-profile:" + match_norm(author.get("name") or "")
            authors.setdefault(source_id, {
                "source_id": source_id,
                "name": author.get("name"),
                "nber_profile": url,
            })
            author_papers[source_id].add(paper["id"])

    print(f"Audit queue: {len(queue)} rows; {len(authors)} official author profiles", flush=True)
    pages: dict[str, str] = {}
    existing_sources = {}
    if args.reuse_sources and (ROOT / "nber_si" / "data" / "cv_audit_sources.json").exists():
        existing_sources = {
            row.get("source_id") or row.get("nber_profile")
            or "missing-profile:" + match_norm(row.get("name") or ""): row
            for row in json.loads((ROOT / "nber_si" / "data" / "cv_audit_sources.json").read_text())
        }
    # Reuse successful source records, but explicitly retry prior profile
    # failures. Otherwise --reuse-sources made those failures permanent.
    to_fetch = [source_id for source_id, author in authors.items()
                if author.get("nber_profile") and (
                    source_id not in existing_sources
                    or (
                        not existing_sources[source_id].get("profile_fetch_ok")
                        and existing_sources[source_id].get("profile_fetch_state")
                        not in {"exhausted_unavailable", "not_applicable"}
                    )
                )]
    if args.skip_profile_retries:
        to_fetch = []
    if to_fetch:
        print(f"Fetching NBER profiles not in source cache: {len(to_fetch)}", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(fetch, authors[source_id]["nber_profile"], "nber_profiles", args.refresh): source_id
                for source_id in to_fetch
            }
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                pages[futures[future]] = future.result()
                if n % 250 == 0:
                    print(f"  profiles {n}/{len(futures)}", flush=True)

    sources = []
    for source_id, author in authors.items():
        previous = existing_sources.get(source_id, {})
        fetched = pages.get(source_id, "")
        links = external_links(fetched) if fetched and "FETCH_ERROR" not in fetched else previous.get("external_pages", [])
        has_profile = bool(author.get("nber_profile"))
        fetch_ok = ("FETCH_ERROR" not in fetched if fetched else bool(previous.get("profile_fetch_ok"))) if has_profile else False
        fetch_attempts = int(previous.get("profile_fetch_attempts") or 0) + int(source_id in pages)
        sources.append({
            **author,
            "paper_ids": sorted(author_papers[source_id]),
            "external_pages": links,
            "web_search_pages": previous.get("web_search_pages", []),
            "web_search_attempts": int(previous.get("web_search_attempts") or 0),
            "web_search_state": previous.get("web_search_state"),
            "profile_fetch_ok": fetch_ok,
            "profile_fetch_attempts": fetch_attempts,
            "profile_fetch_state": (
                "not_applicable" if not has_profile
                else "complete" if fetch_ok
                else "exhausted_unavailable" if fetch_attempts >= 3
                else "pending"
            ),
        })

    if args.web_search:
        search_sources = [source for source in sources if args.web_search_all or not source["external_pages"]]
        if args.web_search_only_unattempted:
            search_sources = [source for source in search_sources
                              if source.get("web_search_state") not in {
                                  "complete", "no_hit", "candidate", "not_applicable", "exhausted_unavailable"
                              }]
        search_sources.sort(key=lambda source: ((source.get("name") or "").casefold(), source.get("source_id") or ""))
        if args.web_search_offset:
            search_sources = search_sources[args.web_search_offset:]
        if args.web_search_limit:
            search_sources = search_sources[:args.web_search_limit]
        print(f"Web-search author pages: {len(search_sources)} (offset {args.web_search_offset})", flush=True)
        discovered_by_profile = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.web_search_workers) as executor:
            futures = {
                executor.submit(discover_web_pages, source.get("name") or "", args.refresh,
                                args.web_search_timeout): source
                for source in search_sources
            }
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                source = futures[future]
                discovered_by_profile[source["source_id"]] = future.result()
                if n % 100 == 0:
                    print(f"  web-search {n}/{len(search_sources)}", flush=True)
        for source in search_sources:
            discovered = discovered_by_profile.get(source["source_id"], [])
            source["web_search_pages"] = discovered
            search_queries = [
                f'"{source.get("name") or ""}" economist homepage research',
                f'"{source.get("name") or ""}" economics CV research',
            ]
            query_states = []
            for query in search_queries:
                path = cache_key_path("search", "ddg:" + query)
                body = path.read_text(errors="replace") if path.exists() else ""
                query_states.append("complete" if body and "FETCH_ERROR" not in body else "pending")
            previous_attempts = int(source.get("web_search_attempts") or 0)
            failures = sum(state != "complete" for state in query_states)
            source["web_search_attempts"] = previous_attempts + 1
            source["web_search_state"] = (
                "complete" if not failures
                else "exhausted_unavailable" if previous_attempts >= 2
                else "pending"
            )
            merged = {item["url"].rstrip("/"): item for item in source["external_pages"]}
            for item in discovered:
                merged.setdefault(item["url"].rstrip("/"), item)
            source["external_pages"] = list(merged.values())

    candidates = []
    title_seen: dict[str, list[dict]] = defaultdict(list)
    if args.external or args.documents:
        ext_urls = sorted({link["url"] for source in sources for link in source["external_pages"]})
        print(f"External author pages: {len(ext_urls)}", flush=True)
        ext_pages: dict[str, str] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(fetch, url, "external_pages", args.refresh): url for url in ext_urls}
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                ext_pages[futures[future]] = future.result()
                if n % 250 == 0:
                    print(f"  external {n}/{len(futures)}", flush=True)
        by_id = {paper["id"]: paper for paper in queue}
        for source in sources:
            docs = []
            for external in source["external_pages"]:
                page = ext_pages.get(external["url"], "")
                docs.extend(likely_documents(page, external["url"]))
                sibling_titles = [by_id[pid]["title"] for pid in source["paper_ids"]]
                normalized_page = match_norm(visible_text(page))
                for paper_id in source["paper_ids"]:
                    paper_title = match_norm(by_id[paper_id]["title"])
                    if len(paper_title.split()) >= 4 and paper_title in normalized_page:
                        title_seen[paper_title].append({"author": source["name"], "evidence_url": external["url"]})
                    evidence = evidence_on_normalized(normalized_page, external["url"], by_id[paper_id], sibling_titles)
                    if evidence:
                        evidence["author"] = source["name"]
                        candidates.append(evidence)
            source["likely_documents"] = list({item["url"]: item for item in docs}.values())

        if args.documents:
            strong_by_author = {}
            strong_urls = set()
            for source in sources:
                strong = []
                for item in source.get("likely_documents", []):
                    clue = norm(item["url"] + " " + item["text"])
                    if re.search(r"\b(cv|curriculum|vitae|vita|research|publications?|working papers?)\b", clue):
                        strong.append(item)
                        strong_urls.add(item["url"])
                strong_by_author[source["source_id"]] = strong
            print(f"Strong CV/vita documents: {len(strong_urls)}", flush=True)
            document_text: dict[str, str] = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.workers, 60)) as executor:
                futures = {executor.submit(fetch_document, url, args.refresh): url for url in strong_urls}
                for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    document_text[futures[future]] = future.result()
                    if n % 100 == 0:
                        print(f"  documents {n}/{len(futures)}", flush=True)
            for source in sources:
                sibling_titles = [by_id[pid]["title"] for pid in source["paper_ids"]]
                for document in strong_by_author[source["source_id"]]:
                    document_body = document_text.get(document["url"], "")
                    normalized_document = match_norm(document_body)
                    for paper_id in source["paper_ids"]:
                        paper_title = match_norm(by_id[paper_id]["title"])
                        if len(paper_title.split()) >= 4 and paper_title in normalized_document:
                            title_seen[paper_title].append({"author": source["name"], "evidence_url": document["url"]})
                        evidence = evidence_on_normalized(normalized_document, document["url"], by_id[paper_id], sibling_titles)
                        if evidence:
                            evidence["author"] = source["name"]
                            evidence["evidence_kind"] = "cv_or_vita"
                            candidates.append(evidence)

        candidate_path = ROOT / "nber_si" / "data" / "cv_audit_candidates.json"
        existing_candidates = json.loads(candidate_path.read_text()) if candidate_path.exists() else []
        candidates = list({
            (row["paper_id"], row["candidate_status"], row["journal"], row["evidence_url"]): row
            for row in [*existing_candidates, *candidates]
        }.values())
        candidate_titles = {match_norm(by_id[row["paper_id"]]["title"])
                            for row in candidates if row["paper_id"] in by_id}
        no_status = []
        for title_key, evidence in sorted(title_seen.items()):
            if title_key in candidate_titles:
                continue
            unique_evidence = list({item["evidence_url"]: item for item in evidence}.values())
            no_status.append({
                "normalized_title": title_key,
                "title": next(p["title"] for p in queue if match_norm(p["title"]) == title_key),
                "evidence": unique_evidence,
                "checked_at": "2026-07-14",
                "result": "exact title found; no named-journal R&R, acceptance, or forthcoming phrase detected near title",
            })
        no_status_path = ROOT / "nber_si" / "data" / "cv_no_status_checks.json"
        existing_no_status = json.loads(no_status_path.read_text()) if no_status_path.exists() else []
        no_status = list({
            row["normalized_title"]: row for row in [*existing_no_status, *no_status]
        }.values())
        candidate_path.write_text(
            json.dumps(candidates, indent=2, ensure_ascii=False) + "\n"
        )
        no_status_path.write_text(
            json.dumps(no_status, indent=2, ensure_ascii=False) + "\n"
        )
    sources.sort(key=lambda x: ((x.get("name") or "").casefold(), x.get("source_id") or ""))
    output = ROOT / "nber_si" / "data" / "cv_audit_sources.json"
    if output.exists():
        existing_output = {
            row.get("source_id") or row.get("nber_profile")
            or "missing-profile:" + match_norm(row.get("name") or ""): row
            for row in json.loads(output.read_text())
        }
        for source in sources:
            source_id = source.get("source_id") or source.get("nber_profile") or "missing-profile:" + match_norm(source.get("name") or "")
            previous = existing_output.get(source_id, {})
            merged_source = {**previous, **source}
            page_map = {item["url"].rstrip("/"): item for item in previous.get("external_pages", [])}
            for item in source.get("external_pages", []):
                page_map.setdefault(item["url"].rstrip("/"), item)
            merged_source["external_pages"] = list(page_map.values())
            if previous.get("likely_documents") and not source.get("likely_documents"):
                merged_source["likely_documents"] = previous["likely_documents"]
            existing_output[source_id] = merged_source
        sources = sorted(existing_output.values(), key=lambda x: (
            (x.get("name") or "").casefold(), x.get("source_id") or x.get("nber_profile") or ""
        ))
    output.write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "authors": len(sources),
        "profile_fetch_ok": sum(x["profile_fetch_ok"] for x in sources),
        "authors_with_external_page": sum(bool(x["external_pages"]) for x in sources),
        "unique_external_pages": len({l["url"] for x in sources for l in x["external_pages"]}),
        "web_search_pages": sum(len(x.get("web_search_pages", [])) for x in sources),
        "likely_documents": sum(len(x.get("likely_documents", [])) for x in sources),
        "status_candidates": len(candidates),
        "title_lineages_checked_without_named_status": len(no_status) if (args.external or args.documents) else 0,
        "output": str(output.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
