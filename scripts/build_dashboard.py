#!/usr/bin/env python3
"""Merge agenda data with publication lookups and build the dashboard.

Inputs:  data/papers.json            (one entry per paper on a conference agenda)
         data/lookups/batch-*.json   (publication lookups; batch-18 may add utah2019 papers)
Outputs: data/papers_enriched.json   (merged, normalized)
         data/papers_enriched.csv
         dashboard/index.html        (template with data inlined)
"""
import csv
import glob
import json
import os
import re

proj_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Canonical journal names: collapse common abbreviations/variants.
JOURNAL_MAP = {
    "aer": "American Economic Review",
    "american economic review": "American Economic Review",
    "aer: insights": "American Economic Review: Insights",
    "american economic review: insights": "American Economic Review: Insights",
    "aea papers and proceedings": "AEA Papers & Proceedings",
    "aea papers & proceedings": "AEA Papers & Proceedings",
    "american economic review papers and proceedings": "AEA Papers & Proceedings",
    "qje": "Quarterly Journal of Economics",
    "quarterly journal of economics": "Quarterly Journal of Economics",
    "the quarterly journal of economics": "Quarterly Journal of Economics",
    "jpe": "Journal of Political Economy",
    "journal of political economy": "Journal of Political Economy",
    "econometrica": "Econometrica",
    "restud": "Review of Economic Studies",
    "review of economic studies": "Review of Economic Studies",
    "the review of economic studies": "Review of Economic Studies",
    "rand journal of economics": "RAND Journal of Economics",
    "the rand journal of economics": "RAND Journal of Economics",
    "rand": "RAND Journal of Economics",
    "restat": "Review of Economics and Statistics",
    "review of economics and statistics": "Review of Economics and Statistics",
    "the review of economics and statistics": "Review of Economics and Statistics",
    "american economic journal: microeconomics": "AEJ: Microeconomics",
    "aej: microeconomics": "AEJ: Microeconomics",
    "aej: micro": "AEJ: Microeconomics",
    "american economic journal: applied economics": "AEJ: Applied Economics",
    "aej: applied economics": "AEJ: Applied Economics",
    "aej: applied": "AEJ: Applied Economics",
    "american economic journal: economic policy": "AEJ: Economic Policy",
    "aej: economic policy": "AEJ: Economic Policy",
    "aej: policy": "AEJ: Economic Policy",
    "american economic journal: macroeconomics": "AEJ: Macroeconomics",
    "aej: macroeconomics": "AEJ: Macroeconomics",
    "journal of econometrics": "Journal of Econometrics",
    "journal of labor economics": "Journal of Labor Economics",
    "journal of public economics": "Journal of Public Economics",
    "journal of health economics": "Journal of Health Economics",
    "journal of finance": "Journal of Finance",
    "the journal of finance": "Journal of Finance",
    "journal of financial economics": "Journal of Financial Economics",
    "journal of economic theory": "Journal of Economic Theory",
    "theoretical economics": "Theoretical Economics",
    "management science": "Management Science",
    "marketing science": "Marketing Science",
    "international journal of industrial organization": "International Journal of Industrial Organization",
    "journal of industrial economics": "Journal of Industrial Economics",
    "the journal of industrial economics": "Journal of Industrial Economics",
    "journal of the european economic association": "Journal of the European Economic Association",
    "jeea": "Journal of the European Economic Association",
    "journal of urban economics": "Journal of Urban Economics",
    "journal of law and economics": "Journal of Law and Economics",
    "the journal of law and economics": "Journal of Law and Economics",
    "journal of economic perspectives": "Journal of Economic Perspectives",
    "review of financial studies": "Review of Financial Studies",
    "the review of financial studies": "Review of Financial Studies",
    "quantitative economics": "Quantitative Economics",
    "quantitative marketing and economics": "Quantitative Marketing and Economics",
    "american economic review: p&p": "AEA Papers & Proceedings",
}

STATUS_ORDER = {"published": 0, "forthcoming": 1, "rr": 2, "working_paper": 3, "not_found": 4}

# Papers currently under a revise-and-resubmit (R&R) at a named journal, read off
# the lookup `note` fields. The original lookups classed these as "working_paper"
# (an R&R is not an acceptance); this normalization layer promotes them to their
# own "rr" status so they can be shown distinctly and optionally counted toward
# the journal figures. Value = the R&R target journal (canonicalized by norm_journal).
RR_JOURNAL = {
    "nber2017-06": "AEJ: Economic Policy",
    "nber2017-08": "RAND Journal of Economics",
    "nber2018-05": "American Economic Review",
    "nber2019-09": "Review of Economic Studies",
    "nber2022-07": "Review of Economic Studies",
    "nber2023-01": "American Economic Review",
    "nber2023-02": "Econometrica",
    "nber2023-04": "American Economic Review",
    "nber2023-07": "Management Science",
    "nber2023-12": "AEJ: Microeconomics",
    "nber2023-13": "American Economic Review",
    "nber2024-03": "Marketing Science",
    "nber2024-04": "American Economic Review",
    "nber2024-08": "Journal of Political Economy",
    "nber2025-02": "Journal of Political Economy",
    "nber2025-04": "Econometrica",
    "nber2025-10": "American Economic Review",
    "utah2016-08": "Journal of Financial Economics",
    "utah2020-03": "American Economic Review",
    "utah2022-07": "American Economic Review",
    "utah2023-01": "American Economic Review",
    "utah2023-02": "American Economic Review",
    "utah2023-07": "Econometrica",
    "utah2024-03": "Review of Economic Studies",
    "utah2024-06": "American Economic Review",
    "utah2025-02": "Quarterly Journal of Economics",
    "utah2025-08": "Journal of Finance",
    # Added after a July 2026 recheck of every non-R&R working paper's authors'
    # CVs/websites — these were R&R (incl. "major revision" / "revision requested"
    # / 2nd-round R&R) but had been logged as plain working papers.
    "nber2016-06": "Journal of Political Economy",
    "nber2019-05": "Journal of Political Economy",
    "nber2023-03": "Quarterly Journal of Economics",
    "nber2024-02": "Econometrica",
    "nber2025-07": "Journal of Political Economy",
    "nber2026-07": "American Economic Review",
    "utah2025-06": "Econometrica",
    "utah2026-03": "American Economic Review",
}

# Fresh notes for R&R papers whose original lookup note predates the recheck (so
# the displayed note doesn't contradict the new R&R status). Keyed by id; papers
# not listed here keep the note from their batch lookup.
RR_NOTE = {
    "nber2016-06": "R&R (\"major revision\") at the Journal of Political Economy per Fanyin Zheng's CV (rechecked Jul 2026); circulates as a Columbia/SSRN working paper, not yet published.",
    "nber2019-05": "Retitled \"Vertical Integration and Plan Design in Healthcare Markets\" (NBER WP 32833); R&R (\"revision requested\") at the Journal of Political Economy per Benjamin Vatter's website (rechecked Jul 2026).",
    "nber2023-03": "NBER WP 33187; R&R at the Quarterly Journal of Economics per coauthor Edward Kong's publications page (rechecked Jul 2026).",
    "nber2024-02": "NBER WP 32670; second-round R&R at Econometrica per Christopher Neilson's research page (rechecked Jul 2026) — earlier logged only as 'under review'.",
    "nber2025-07": "SSRN working paper (job market paper); R&R at the Journal of Political Economy per Camilla Schneier's website (rechecked Jul 2026).",
    "nber2026-07": "NBER WP 33832 (also CEPR DP20268 / SSRN 5253368); R&R at the American Economic Review per Ashley Swanson's Feb 2026 CV and Panle Jia Barwick's research page (rechecked Jul 2026).",
    "utah2025-06": "NBER WP 33903 (also SSRN 5285984); R&R at Econometrica per Zoe Cullen's research page (rechecked Jul 2026).",
    "utah2026-03": "NBER WP 34506; working-paper title \"Paternalistic Social Assistance: Evidence and Implications from Cash vs. In-Kind Transfers\"; R&R at the American Economic Review per Amy Finkelstein's MIT working-papers page (rechecked Jul 2026).",
}


def norm_journal(name):
    if not name:
        return None
    key = re.sub(r"\s+", " ", name.strip()).lower().rstrip(".")
    return JOURNAL_MAP.get(key, name.strip())


def norm_status(s):
    if not s:
        return "not_found"
    s = s.strip().lower().replace(" ", "_").replace("-", "_")
    if s in ("published", "forthcoming", "working_paper", "not_found", "rr"):
        return s
    if s in ("r&r", "revise_and_resubmit", "revise_&_resubmit", "reject_and_resubmit"):
        return "rr"
    if "forthcoming" in s or "accepted" in s:
        return "forthcoming"
    if "publish" in s:
        return "published"
    if "working" in s or "wp" == s:
        return "working_paper"
    return "not_found"


def main():
    papers = {p["id"]: dict(p) for p in json.load(open(os.path.join(proj_path, "data/papers.json")))}

    lookup_files = sorted(glob.glob(os.path.join(proj_path, "data/lookups/batch-*.json")))
    n_lookups = 0
    for f in lookup_files:
        try:
            entries = json.load(open(f))
        except json.JSONDecodeError as e:
            print(f"WARNING: could not parse {f}: {e}")
            continue
        for e in entries:
            pid = e.get("id")
            if not pid:
                continue
            if pid not in papers:
                # batch-18 style: new papers (recovered Utah 2019 program)
                papers[pid] = {
                    "id": pid,
                    "conference": e.get("conference", "Utah WBEC"),
                    "year": e.get("year"),
                    "title": e.get("title"),
                    "agenda_authors": e.get("agenda_authors"),
                }
            p = papers[pid]
            st = norm_status(e.get("status"))
            if pid in RR_JOURNAL:
                st = "rr"
            p["status"] = st
            if st == "rr":
                # journal from the curated map (old batches) or the lookup itself (new batches)
                p["journal"] = norm_journal(RR_JOURNAL.get(pid) or e.get("journal"))
            elif st in ("published", "forthcoming"):
                p["journal"] = norm_journal(e.get("journal"))
            else:
                p["journal"] = None
            p["pub_year"] = e.get("pub_year") if st == "published" else None
            p["published_title"] = e.get("published_title")
            p["authors"] = e.get("authors") or p.get("agenda_authors")
            p["url"] = e.get("url")
            p["note"] = RR_NOTE.get(pid, e.get("note"))
            n_lookups += 1

    merged = sorted(papers.values(), key=lambda p: (p["conference"], p["year"], p["id"]))
    for p in merged:
        p.setdefault("status", "not_found")
        p.setdefault("journal", None)
        p.setdefault("pub_year", None)
        p.setdefault("authors", p.get("agenda_authors"))
        if p["status"] == "published" and p["pub_year"] and p.get("year"):
            p["lag"] = p["pub_year"] - p["year"]
        else:
            p["lag"] = None

    out_json = os.path.join(proj_path, "data/papers_enriched.json")
    json.dump(merged, open(out_json, "w"), indent=1)

    cols = ["id", "conference", "year", "title", "agenda_authors", "authors", "status",
            "journal", "pub_year", "lag", "published_title", "url", "note"]
    with open(os.path.join(proj_path, "data/papers_enriched.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged)

    template = open(os.path.join(proj_path, "dashboard/template.html")).read()
    html = template.replace("/*__DATA_JSON__*/[]", json.dumps(merged, separators=(",", ":")))
    open(os.path.join(proj_path, "dashboard/index.html"), "w").write(html)

    n_pub = sum(1 for p in merged if p["status"] == "published")
    print(f"{len(merged)} papers; {n_lookups} lookups merged from {len(lookup_files)} batches; "
          f"{n_pub} published, {sum(1 for p in merged if p['status']=='forthcoming')} forthcoming, "
          f"{sum(1 for p in merged if p['status']=='rr')} R&R, "
          f"{sum(1 for p in merged if p['status']=='working_paper')} working paper, "
          f"{sum(1 for p in merged if p['status']=='not_found')} not found")


if __name__ == "__main__":
    main()
