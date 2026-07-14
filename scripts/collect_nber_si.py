#!/usr/bin/env python3
"""Collect NBER Summer Institute meeting agendas from official NBER pages.

The public conference pages load agendas from ``/api/conference/{node}/agenda``.
This collector starts from each annual Summer Institute schedule, discovers every
meeting page, and stores one row per research-paper presentation. Non-paper agenda
items (breaks, panels without papers, lectures without a paper record) are omitted.

Network responses are cached under ``nber_si/cache``. Use ``--refresh`` to replace
the cache and ``--start-year``/``--end-year`` to change the collection window.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.nber.org"
DEFAULT_START = 2015
DEFAULT_END = 2026


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", html.unescape("".join(self._text))).strip()
            self.links.append((self._href, text))
            self._href = None
            self._text = []


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def clean_text(value: str | None) -> str:
    """Remove presentation markup returned inside NBER API text fields."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def fetch(url: str, path: Path, refresh: bool = False) -> bytes:
    if path.exists() and not refresh:
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "conference-to-pub/1.0 (research dataset)"})
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            path.write_bytes(payload)
            return payload
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def schedule_meetings(page: str, year: int) -> list[dict]:
    parser = LinkParser()
    parser.feed(page)
    prefix = f"/conferences/si-{year}-"
    found: dict[str, dict] = {}
    for href, text in parser.links:
        clean = href.split("?", 1)[0].rstrip("/")
        if clean.startswith(prefix) and clean != f"/conferences/summer-institute-{year}":
            found.setdefault(clean, {"year": year, "meeting_title": text, "meeting_url": BASE + clean})
    return list(found.values())


def page_metadata(page: str) -> tuple[int, str | None, str | None]:
    node = re.search(r"\bnodeId\s*=\s*(\d+)", page)
    if not node:
        raise ValueError("conference page has no nodeId")
    conf = re.search(r"simple_printable\?conf_id=([^\"&]+)", page)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, flags=re.I | re.S)
    title = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else None
    return int(node.group(1)), conf.group(1) if conf else None, html.unescape(title) if title else None


def paper_row(item: dict, meeting: dict, sequence: int) -> dict | None:
    paper = item.get("paper")
    if not isinstance(paper, dict):
        return None
    record = paper.get("record") or {}
    title = record.get("title") or record.get("alt_title")
    if not title:
        return None
    authors = [clean_text(a.get("name")) for a in paper.get("author_with_objs_array", []) if a.get("name")]
    author_profiles = []
    for author in paper.get("author_with_objs_array", []):
        obj = author.get("obj") or author.get("user") or {}
        if author.get("name"):
            author_profiles.append({"name": clean_text(author["name"]), "nber_url": obj.get("url")})
    date = (item.get("record") or {}).get("schedule_date")
    paper_id = record.get("id") or (item.get("record") or {}).get("paper") or f"paper-{sequence:02d}"
    return {
        "id": f"nbersi-{meeting['year']}-{meeting['meeting_slug']}-{paper_id}",
        "program": meeting["program"],
        "program_slug": meeting["program_slug"],
        "meeting_title": meeting["meeting_title"],
        "year": meeting["year"],
        "date": date,
        "title": clean_text(str(title)),
        "agenda_authors": ", ".join(authors),
        "authors_list": authors,
        "author_profiles": author_profiles,
        "paper_url": paper.get("conference_program_paper_url"),
        "nber_working_paper": paper.get("conf_presented_pnum"),
        "meeting_url": meeting["meeting_url"],
        "source": "NBER conference agenda API",
    }


def canonical_program(title: str) -> str:
    # Keep the meeting taxonomy recognizable while joining a few purely stylistic
    # title changes. More aliases can be added without touching raw meeting titles.
    clean = re.sub(r"^SI\s+\d{4}\s*[-–—:]?\s*", "", title, flags=re.I).strip()
    aliases = {
        "aging": "Aging",
        "aging/social security": "Aging",
        "workshop on aging": "Aging",
        "industrial organization": "Industrial Organization",
        "public economics": "Public Economics",
        "labor studies": "Labor Studies",
        "development economics": "Development Economics",
        "monetary economics": "Monetary Economics",
        "corporate finance": "Corporate Finance",
        "asset pricing": "Asset Pricing",
        "law and economics": "Law and Economics",
        "urban economics": "Urban Economics",
        "economics of health": "Economics of Health",
        "economics of education": "Economics of Education",
        "political economy": "Political Economy",
        "household finance": "Household Finance",
        "environment and energy economics": "Environment and Energy Economics",
        "environmental & energy economics": "Environment and Energy Economics",
        "children": "Children and Families",
        "crime": "Economics of Crime",
        "economics of crime working group": "Economics of Crime",
        "education": "Economics of Education",
        "health care": "Economics of Health",
        "health economics": "Economics of Health",
        "economics of it and digitization": "Digital Economics and Artificial Intelligence",
        "economics of it and digitization workshop": "Digital Economics and Artificial Intelligence",
        "it and digitization": "Digital Economics and Artificial Intelligence",
        "entrepreneurship workshop": "Entrepreneurship",
        "household finance meeting": "Household Finance",
        "income distribution and macroeconomics": "Inequality and Macroeconomics",
        "inequality and the macroeconomy": "Inequality and Macroeconomics",
        "international trade & macroeconomics": "International Trade and Macroeconomics",
        "law & economics": "Law and Economics",
        "monetary economics workshop": "Monetary Economics",
        "political economy workshop": "Political Economy",
        "social security": "Economics of Social Security",
        "public econ. taxation & social insurance": "Public Economics",
        "nber/criw workshop": "Conference on Research in Income and Wealth",
        "research on income and wealth": "Conference on Research in Income and Wealth",
        "dynamic equilibrium models": "Dynamic Equilibrium Models",
        "workshop on methods and applications for dynamic equilibrium models": "Dynamic Equilibrium Models",
        "economic growth": "Economic Growth and Long-Run Macroeconomic Development",
        "ifm data sources project": "International Finance and Macroeconomics Data Sources",
        "international finance and macroeconomic data sources": "International Finance and Macroeconomics Data Sources",
        "international finance and macroeconomics data session": "International Finance and Macroeconomics Data Sources",
        "efg behavioral/macro": "Behavioral Macro",
        "efg price dynamics": "Price Dynamics",
        "efg working group - price dynamics": "Price Dynamics",
        "gender in the economy: change and persistence of norms": "Gender in the Economy",
        "macro, money and financial markets": "Macro, Money and Financial Frictions",
    }
    return aliases.get(clean.casefold(), clean)


def collect_meeting(discovered: dict, cache: Path, refresh: bool) -> tuple[dict, list[dict]]:
    page_slug = discovered["meeting_url"].rsplit("/", 1)[-1]
    page = fetch(discovered["meeting_url"], cache / "meetings" / f"{page_slug}.html", refresh).decode("utf-8", "replace")
    node_id, conf_id, page_title = page_metadata(page)
    agenda_url = f"{BASE}/api/conference/{node_id}/agenda"
    agenda = json.loads(fetch(agenda_url, cache / "agendas" / f"{page_slug}.json", refresh))
    meeting_title = page_title or discovered["meeting_title"] or page_slug
    program = canonical_program(meeting_title)
    meeting = {
        **discovered,
        "meeting_title": meeting_title,
        "meeting_slug": page_slug,
        "program": program,
        "program_slug": slugify(program),
        "node_id": node_id,
        "conf_id": conf_id,
        "agenda_url": agenda_url,
    }
    meeting_papers = [row for n, item in enumerate(agenda.get("items", []), 1)
                      if (row := paper_row(item, meeting, n))]
    meeting["paper_count"] = len(meeting_papers)
    return meeting, meeting_papers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=DEFAULT_START)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    base = ROOT / "nber_si"
    cache = base / "cache"
    meetings: list[dict] = []
    papers: list[dict] = []

    for year in range(args.start_year, args.end_year + 1):
        schedule_url = f"{BASE}/conferences/summer-institute-{year}"
        schedule = fetch(schedule_url, cache / f"schedule-{year}.html", args.refresh).decode("utf-8", "replace")
        year_meetings = schedule_meetings(schedule, year)
        print(f"{year}: {len(year_meetings)} meeting pages")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(collect_meeting, discovered, cache, args.refresh): discovered
                       for discovered in year_meetings}
            for future in concurrent.futures.as_completed(futures):
                discovered = futures[future]
                try:
                    meeting, meeting_papers = future.result()
                except Exception as exc:
                    print(f"  WARNING {discovered['meeting_url']}: {exc}")
                    continue
                meetings.append(meeting)
                papers.extend(meeting_papers)

    base.mkdir(exist_ok=True)
    (base / "data").mkdir(exist_ok=True)
    meetings.sort(key=lambda m: (m["year"], m["meeting_title"]))
    papers.sort(key=lambda p: (p["year"], p["program"], p["date"] or "", p["id"]))
    # A small number of NBER API agendas repeat the same paper record in the
    # same canonical program-year. Count a presentation once, matching the
    # hand-cleaned IO series and avoiding duplicate dashboard appearances.
    unique_papers, seen = [], set()
    for paper in papers:
        key = (paper["year"], paper["program_slug"], slugify(paper["title"]))
        if key in seen:
            continue
        seen.add(key)
        unique_papers.append(paper)
    duplicate_rows_removed = len(papers) - len(unique_papers)
    papers = unique_papers
    (base / "data" / "meetings.json").write_text(json.dumps(meetings, indent=2, ensure_ascii=False) + "\n")
    (base / "data" / "papers.json").write_text(json.dumps(papers, indent=2, ensure_ascii=False) + "\n")
    programs = sorted({p["program"] for p in papers})
    summary = {
        "snapshot": "2026-07-14",
        "start_year": args.start_year,
        "end_year": args.end_year,
        "meeting_count": len(meetings),
        "paper_appearances": len(papers),
        "duplicate_agenda_rows_removed": duplicate_rows_removed,
        "program_count": len(programs),
        "programs": programs,
    }
    (base / "data" / "collection_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
