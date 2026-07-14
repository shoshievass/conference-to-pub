#!/usr/bin/env python3
"""Convert manually reviewed author-page candidates into the curated SI audit."""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean_author(value):
    """Normalize display artifacts without conflating distinct authors."""
    return re.sub(r"<[^>]+>", "", value or "").strip()


def matching_evidence(rows, status, journal):
    """Return at most one supporting source per author for the final decision."""
    evidence = []
    seen_authors = set()
    for row in rows:
        author = clean_author(row.get("author"))
        author_key = norm(author)
        if (not author_key or author_key in seen_authors
                or row.get("candidate_status") != status
                or row.get("journal") != journal):
            continue
        seen_authors.add(author_key)
        evidence.append({
            "author": author,
            "evidence_url": row["evidence_url"],
            "status_phrase": row["status_phrase"],
        })
    return evidence


# Manual review on 2026-07-14: the detector crossed into an adjacent project's
# status in each case, so these candidates must not be applied.
REJECT = {
    norm("How to Sell Public Debt in Uncertain Times"),
    norm("Climate Change, Deforestation, and the Expansion of the Global Agricultural Frontier"),
    norm("Quotas in General Equilibrium"),
    norm("Simple Models and Biased Forecasts"),
    norm("The Breakdown of the English Society of Orders: The role of the Industrial Revolution"),
    norm("Competition and Fraud in Health Care"),
    norm("Asset Returns as Carbon Taxes"),
    norm("Sophisticated Borrowing Constraints and Macroeconomic Dynamics"),
    norm("A Currency Premium Puzzle"),
    norm("Schooling and Political Activism in the Early Civil Rights Era"),
    norm("Police Patrols and Crime"),
    norm("Monopsony, Markdowns, and Minimum Wages"),
    norm("Quick-Fixing: Near-Rationality in Consumption and Savings Behavior"),
    norm("Pricing and Production without the Invisible Hand"),
    norm("The Global Effects of Carbon Border Adjustment Mechanisms"),
    norm("Critical Minerals, Geopolitics, and the Green Transition"),
    norm("Fundamentally, Momentum is Fundamental Momentum"),
    norm("Accounting for Credibility: Fiscal-Monetary Interactions and the Credibility of Central Bank Mandates"),
    norm("The Impact of a Child with Down Syndrome"),
    norm("Does Homeownership Matter? The Long-Term Consequences of Losing a House during the Great Recession"),
    norm("Tariff Wars and Net Foreign Assets"),
    norm("Emigration during Turbulent Times"),
    norm("Causal Inference in Financial Event Studies"),
    norm("The Life-Cycle of Concentrated Industries"),
    norm("Measuring Valuation of Liquidity with Penalized Withdrawals"),
    norm("A Model of U.S. Monetary Policy and the Global Financial Cycle"),
    norm("Identifying Policy Causal Effects from Rule Changes"),
    norm("The Psychosocial Value of Employment"),
    norm("Payments, Reserves, and Financial Fragility"),
    norm("Did Foreigners Pay America's Tariffs? Quantity Discounts, Scale Economies and Incomplete Pass-Through"),
    norm("A Theory of Firm Wage Dynamics"),
    norm("Firm Premia and Match Effects in Pay vs. Amenities"),
    norm("The Labor Supply Curve is Upward Sloping: The Labor Market Effects of Immigrant-Induced Demand Shocks"),
    norm("Community Impacts of Mass Incarceration"),
    norm("Unconventional Monetary Policy According to HANK"),
    norm("How Does Data Access Shape Science? Evidence from the Impact of U.S. Census’s Research Data Centers on Economics Research"),
    norm("Decoding China's Industrial Policies"),
    norm("Monopsony and Backloaded Compensation: Theory and Evidence from Public Accountants"),
    norm("Doctors as Gatekeepers in Social Insurance: Evidence from Workers’ Compensation Insurance"),
    norm("The Effect of Foreclosures on Homeowners, Tenants, and Landlords"),
    norm("Consumer Bankruptcy as Aggregate Demand Management"),
    norm("Optimal Long-Run Fiscal Policy with Heterogeneous Agents"),
    norm("A Long View of Employment Growth and Firm Dynamics in the United States: Importers vs. Exporters vs. Non-Traders"),
    norm("Deficits and Inflation: HANK meets FTPL"),
    norm("College Major Restrictions and Student Stratification"),
    norm("The Impact of Central Bank Stock Purchases: Evidence from Discontinuities in Policy Rules"),
    norm("The Power of the Common Task Framework"),
    norm("Antidepressant Treatment in Childhood"),
    norm("Beyond the War: Public Service and the Transmission of Gender Norms"),
    norm("Inelastic Demand at the Extensive and Intensive Margins"),
    norm("Labor Market Fluidity, On-the-Job Learning, and Career Growth Across Countries"),
    norm("Longevity and Occupational Choice"),
    norm("Structural Reinforcement Learning for Heterogeneous Agent Macroeconomics"),
    norm("The Great Game: A Model of Geoeconomic Competition"),
    norm("The Price and Distributional Impact of Flood Risk Disclosure: Evidence from US Housing Platforms"),
    norm("What Do $40 Trillion of Portfolio Holdings Say about Monetary Policy Transmission?"),
    norm("Quality in the Generic Drug Market"),
    norm("Local and National Concentration Trends in Jobs and Sales: The Role of Structural Transformation"),
}

# A newer July 2026 coauthor page reports conditional acceptance, superseding
# another coauthor page's older R&R label.
PUBLISHED_OVERRIDE = norm("Learning about Housing Cost: Survey Evidence from the German House Price Boom")

PUBLISHED_OVERRIDES = {
    norm("Counterproductive Sustainable Investing: The Impact Elasticity of Brown and Green Firms"): "Journal of Finance",
    norm("Why do Workers Dislike Inflation? Wage Erosion and Conflict Costs"): "Econometrica",
    norm("Fiscal Policy in a Networked Economy"): "AEJ: Macroeconomics",
}

JOURNAL_OVERRIDE = {
    norm("Genetic Endowments, Income Dynamics, and Wealth Accumulation Over the Lifecycle"): "AEJ: Macroeconomics",
    norm("Micro Responses to Macro Shocks"): "Journal of Political Economy Microeconomics",
    norm("Demographic Transitions Across Time and Space"): "Journal of Political Economy Macroeconomics",
    norm("Responsible Sourcing? Theory and Evidence from Costa Rica"): "American Economic Review",
}

MANUAL_CONFIRMED = [
    {
        "normalized_title": norm("Earnings Instability"),
        "title": "Earnings Instability",
        "status": "rr",
        "journal": "Quarterly Journal of Economics",
        "pub_year": None,
        "evidence_url": "https://docs.google.com/document/d/1AFkezWRQeyNgGjDxR16zsghw4pkiKJRnnGbLnAr_SPI/",
        "evidence_author": "Peter Ganong",
        "evidence_phrase": "revise and resubmit",
        "reviewed_at": "2026-07-14",
        "evidence": [
            {
                "author": "Peter Ganong",
                "evidence_url": "https://docs.google.com/document/d/1AFkezWRQeyNgGjDxR16zsghw4pkiKJRnnGbLnAr_SPI/",
                "status_phrase": "revise and resubmit",
            },
            {
                "author": "Christina Patterson",
                "evidence_url": "https://www.christinahydepatterson.com/_files/ugd/32299b_2fd3cc152f654155853ad0ed48d0e284.pdf",
                "status_phrase": "revise and resubmit",
            },
        ],
    },
    {
        "normalized_title": norm("How Small is Small? Non-linearities in Heterogeneous Agent Models"),
        "title": "How Small is Small? Non-linearities in Heterogeneous Agent Models",
        "status": "published",
        "journal": "Journal of Economic Theory",
        "pub_year": None,
        "evidence_url": "http://www.javierbianchi.com/",
        "evidence_author": "Javier Bianchi",
        "evidence_phrase": "forthcoming",
        "reviewed_at": "2026-07-14",
    },
    {
        "normalized_title": norm("The Long-run Effect of Air Pollution on Survival"),
        "title": "The Long-run Effect of Air Pollution on Survival",
        "status": "published",
        "journal": "American Economic Review",
        "pub_year": None,
        "evidence_url": "http://julianreif.com/cv/reif.cv.pdf",
        "evidence_author": "Julian Reif",
        "evidence_phrase": "conditionally accepted",
        "reviewed_at": "2026-07-14",
    },
    {
        "normalized_title": norm("College as a Marriage Market"),
        "title": "College as a Marriage Market",
        "status": "published",
        "journal": "Review of Economic Studies",
        "pub_year": None,
        "evidence_url": "https://sites.google.com/site/jackmountjoyeconomics/",
        "evidence_author": "Jack Mountjoy",
        "evidence_phrase": "forthcoming",
        "reviewed_at": "2026-07-14",
    },
]


def main():
    candidates = json.loads((ROOT / "nber_si" / "data" / "cv_audit_candidates.json").read_text())
    grouped = defaultdict(list)
    for row in candidates:
        grouped[norm(row["title"])].append(row)

    audit_path = ROOT / "nber_si" / "data" / "cv_audit.json"
    existing = json.loads(audit_path.read_text()) if audit_path.exists() else []
    confirmed_by_title = {row["normalized_title"]: row for row in existing}
    for row in MANUAL_CONFIRMED:
        confirmed_by_title[row["normalized_title"]] = row
    rejected = []
    for title_key, rows in sorted(grouped.items()):
        if title_key == PUBLISHED_OVERRIDE:
            current = next(row for row in rows if row["candidate_status"] == "published")
            confirmed_by_title[title_key] = {
                "normalized_title": title_key, "title": current["title"], "status": "published",
                "journal": "Review of Financial Studies", "pub_year": None,
                "evidence_url": current["evidence_url"], "evidence_author": current["author"],
                "evidence_phrase": "conditionally accepted", "reviewed_at": "2026-07-14",
            }
            continue
        if title_key in PUBLISHED_OVERRIDES:
            current = next((row for row in rows if row["candidate_status"] == "published"), None)
            if current is None:
                continue
            confirmed_by_title[title_key] = {
                "normalized_title": title_key, "title": current["title"], "status": "published",
                "journal": PUBLISHED_OVERRIDES[title_key], "pub_year": None,
                "evidence_url": current["evidence_url"], "evidence_author": current["author"],
                "evidence_phrase": "conditionally accepted", "reviewed_at": "2026-07-14",
            }
            continue
        rr_rows = [row for row in rows if row["candidate_status"] == "rr"]
        if not rr_rows:
            continue
        if title_key in REJECT:
            confirmed_by_title.pop(title_key, None)
            rejected.append({"normalized_title": title_key, "reason": "status belongs to an adjacent project", "candidates": rr_rows})
            continue
        journals = {row["journal"] for row in rr_rows}
        target_override = JOURNAL_OVERRIDE.get(title_key)
        if len(journals) != 1 and not target_override:
            confirmed_by_title.pop(title_key, None)
            rejected.append({"normalized_title": title_key, "reason": "conflicting R&R journals", "candidates": rr_rows})
            continue
        row = next((row for row in rr_rows if row["journal"] == target_override), rr_rows[0])
        confirmed_by_title[title_key] = {
            "normalized_title": title_key, "title": row["title"], "status": "rr",
            "journal": JOURNAL_OVERRIDE.get(title_key, row["journal"]), "pub_year": None,
            "evidence_url": row["evidence_url"], "evidence_author": row["author"],
            "evidence_phrase": row["status_phrase"], "reviewed_at": "2026-07-14",
        }

    data = ROOT / "nber_si" / "data"
    confirmed = sorted(confirmed_by_title.values(), key=lambda row: row["normalized_title"])
    for row in confirmed:
        if row["normalized_title"] in JOURNAL_OVERRIDE:
            row["journal"] = JOURNAL_OVERRIDE[row["normalized_title"]]
        candidates_for_title = grouped.get(row["normalized_title"], [])
        evidence = matching_evidence(candidates_for_title, row["status"], row["journal"])
        if evidence:
            row["evidence"] = evidence
    (data / "cv_audit.json").write_text(json.dumps(confirmed, indent=2, ensure_ascii=False) + "\n")
    (data / "cv_audit_rejected_candidates.json").write_text(json.dumps(rejected, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "confirmed_title_lineages": len(confirmed),
        "confirmed_rr": sum(row["status"] == "rr" for row in confirmed),
        "confirmed_published": sum(row["status"] == "published" for row in confirmed),
        "rejected_title_lineages": len(rejected),
    }, indent=2))


if __name__ == "__main__":
    main()
