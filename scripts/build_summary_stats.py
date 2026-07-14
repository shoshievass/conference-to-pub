#!/usr/bin/env python3
"""Build reproducible cross-conference summary statistics from enriched data."""

from collections import Counter, defaultdict
from math import ceil
from pathlib import Path
import json
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/papers_enriched.json").read_text())
OUT = ROOT / "data/SUMMARY_STATS.md"

CONFERENCES = [
    "Cowles M&M", "FTC Micro", "NBER IO Spring", "NBER SI IO",
    "Northwestern Antitrust", "Utah WBEC",
]
LABEL = {"Cowles M&M": "Cowles Structural Micro / M&M"}
TOP5 = {
    "American Economic Review", "Journal of Political Economy",
    "Quarterly Journal of Economics", "Review of Economic Studies", "Econometrica",
}


def label(conf):
    return LABEL.get(conf, conf)


def norm_title(value):
    value = (value or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def source_key(value):
    """Keep only stable publication identifiers; author/home-page URLs are unsafe."""
    if not value:
        return None
    parsed = urlparse(value.lower())
    host, path = parsed.netloc.removeprefix("www."), parsed.path.rstrip("/")
    if host in {"doi.org", "dx.doi.org"}:
        return "doi:" + path.lstrip("/")
    if host == "aeaweb.org" or host.endswith(".aeaweb.org"):
        match = re.search(r"/articles\?id=([^&]+)", path + ("?" + parsed.query if parsed.query else ""))
        if match:
            return "aea:" + match.group(1)
    return None


class DSU:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[b] = a


def clusters():
    dsu, seen = DSU(len(DATA)), {}
    for i, paper in enumerate(DATA):
        keys = [("title", norm_title(paper.get(k))) for k in ("title", "published_title")]
        keys.append(("source", source_key(paper.get("url"))))
        for key in (k for k in keys if k[1]):
            if key in seen:
                dsu.union(i, seen[key])
            else:
                seen[key] = i
    grouped = defaultdict(list)
    for i, paper in enumerate(DATA):
        grouped[dsu.find(i)].append(paper)
    return list(grouped.values())


def nearest_rank(values, p):
    values = sorted(values)
    return values[max(0, ceil(p * len(values)) - 1)]


def pct(n, d):
    return f"{100 * n / d:.1f}%"


def main():
    lines = [
        "# Conference summary statistics", "",
        "Generated from `data/papers_enriched.json`. A paper presented at multiple conferences is "
        "one appearance at each conference.", "", "## Coverage and status", "",
        "| Conference | Appearances | Published | R&R | Working paper |", "|---|---:|---:|---:|---:|",
    ]
    for conf in CONFERENCES:
        rows = [p for p in DATA if p["conference"] == conf]
        counts = Counter(p["status"] for p in rows)
        lines.append(f"| {label(conf)} | {len(rows)} | {counts['published']} | {counts['rr']} | {counts['working_paper']} |")
    counts = Counter(p["status"] for p in DATA)
    lines += [f"| **All** | **{len(DATA)}** | **{counts['published']}** | **{counts['rr']}** | **{counts['working_paper']}** |", ""]

    lines += [
        "## Top-five journal outcomes", "",
        "Numerator: appearances published or under R&R at AER, JPE, QJE, REStud, or Econometrica. "
        "Denominator: all appearances at that conference.", "",
        "| Conference | Top-five published or R&R | All appearances | Share |", "|---|---:|---:|---:|",
    ]
    for conf in CONFERENCES:
        rows = [p for p in DATA if p["conference"] == conf]
        n = sum(p["status"] in {"published", "rr"} and p.get("journal") in TOP5 for p in rows)
        lines.append(f"| {label(conf)} | {n} | {len(rows)} | {pct(n, len(rows))} |")

    lines += [
        "", "## Conference-to-publication time", "",
        "Journal issue year minus presentation year, for published appearances with an issue year. "
        "Negative values mean a conference presented an already-published paper.", "",
        "| Conference | N | Median | Mean | IQR | Range |", "|---|---:|---:|---:|---:|---:|",
    ]
    for conf in CONFERENCES:
        lags = [p["lag"] for p in DATA if p["conference"] == conf and p["status"] == "published" and p.get("lag") is not None]
        lines.append(
            f"| {label(conf)} | {len(lags)} | {nearest_rank(lags, .5)} | {sum(lags)/len(lags):.2f} | "
            f"{nearest_rank(lags, .25)}–{nearest_rank(lags, .75)} | {min(lags)}–{max(lags)} |"
        )

    grouped = clusters()
    recurring = [g for g in grouped if len({p["conference"] for p in g}) >= 2]
    overlap_by_year = {}
    for year in sorted({p["year"] for p in DATA}):
        denominator = sum(p["year"] == year for p in DATA)
        numerator = 0
        for group in grouped:
            rows = [p for p in group if p["year"] == year]
            if len({p["conference"] for p in rows}) >= 2:
                numerator += len(rows)
        overlap_by_year[year] = (numerator, denominator)
    lines += [
        "", "## Same-year overlap", "",
        "An appearance is overlapping when the same canonical paper appears at more than one conference "
        "in that calendar year.", "", "| Year | Overlapping appearances | All appearances | Share |",
        "|---:|---:|---:|---:|",
    ]
    for year, (n, d) in overlap_by_year.items():
        lines.append(f"| {year} | {n} | {d} | {pct(n, d)} |")

    transitions = Counter()
    first = Counter()
    for group in recurring:
        years_by_conf = defaultdict(set)
        for p in group:
            years_by_conf[p["conference"]].add(p["year"])
        pairs = set()
        for a, ayears in years_by_conf.items():
            for b, byears in years_by_conf.items():
                # Direction is based on each venue's first appearance. A paper that
                # later returns to its original venue should not count both ways.
                if a != b and min(ayears) < min(byears):
                    pairs.add((a, b))
        transitions.update(pairs)
        earliest = min(p["year"] for p in group)
        first_confs = {p["conference"] for p in group if p["year"] == earliest}
        if len(first_confs) == 1 and any(p["conference"] not in first_confs and p["year"] > earliest for p in group):
            first.update(first_confs)

    lines += [
        "", "## Cross-conference recurrence", "",
        f"There are **{len(recurring)}** canonical papers appearing at two or more conferences. "
        f"Of these, **{sum(transitions.values())}** distinct paper/direction transitions occur in a later year.", "",
        "| Earlier conference | Later conference | Papers |", "|---|---|---:|",
    ]
    for (a, b), n in sorted(transitions.items(), key=lambda item: (-item[1], label(item[0][0]), label(item[0][1]))):
        lines.append(f"| {label(a)} | {label(b)} | {n} |")
    lines += ["", "For recurring papers with one unambiguous first conference and a later appearance elsewhere:", "", "| First conference | Papers |", "|---|---:|"]
    for conf, n in sorted(first.items(), key=lambda item: (-item[1], label(item[0]))):
        lines.append(f"| {label(conf)} | {n} |")
    lines += [
        "", "## Matching method", "",
        "Canonical-paper clusters are the transitive closure of exact normalized agenda titles, exact "
        "normalized published titles, and exact DOI/AEA article identifiers. This follows title changes "
        "without merging records merely because they share an author-page URL.", "",
    ]
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
