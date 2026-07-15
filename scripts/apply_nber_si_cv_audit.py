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


def manual_confirmed(title, journal, evidence_url, evidence_author, evidence_phrase="forthcoming", status="published"):
    return {
        "normalized_title": norm(title),
        "title": title,
        "status": status,
        "journal": journal,
        "pub_year": None,
        "evidence_url": evidence_url,
        "evidence_author": evidence_author,
        "evidence_phrase": evidence_phrase,
        "reviewed_at": "2026-07-14",
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

MANUAL_CONFIRMED.extend([
    manual_confirmed("The Labor Market Returns to Delaying Pregnancy", "American Economic Review",
                     "https://gregveramendi.github.io/Veramendi-CV.pdf", "Gregory Veramendi",
                     "conditionally accepted"),
    manual_confirmed("Community Engagement and Public Safety: Evidence from Crime Enforcement Targeting Immigrants",
                     "American Economic Review", "https://elisajacome.github.io/Jacome/Jacome_CV.pdf",
                     "Elisa Jácome"),
    manual_confirmed("Inequality and Racial Backlash: Evidence from the Reconstruction Era and the Freedmen’s Bureau",
                     "American Economic Review", "http://www.ericchyn.com/files/Chyn_Eric_CV_2026.pdf",
                     "Eric Chyn", "conditionally accepted"),
    manual_confirmed("Tax Policy and Investment in a Global Economy", "American Economic Review",
                     "http://www.ericzwick.com/", "Eric Zwick"),
    manual_confirmed("Antitrust Enforcement Increases Economic Activity", "AEJ: Applied Economics",
                     "https://www.taniababina.com/", "Tania Babina", "conditionally accepted"),
    manual_confirmed("Can Small Businesses Survive Chapter 11?", "Journal of Finance",
                     "https://www.xiangzheng.info/", "Xiang Zheng"),
    manual_confirmed("Closing Ranks: Organized Labor and Immigration", "Journal of Political Economy",
                     "https://carlomedici.github.io/home/CarloMedici_Vita.pdf", "Carlo Medici",
                     "conditionally accepted"),
    manual_confirmed("Deadwood Labor? The Effects of Eliminating Employment Protection for Older Workers",
                     "AEJ: Applied Economics", "http://elsa.berkeley.edu/~saez/saezcv.pdf",
                     "Emmanuel Saez"),
    manual_confirmed("Links Between Puzzles in Household Finance: Evidence from Employee Benefit Choices",
                     "AEJ: Economic Policy",
                     "https://www.adamleive.com/wp-content/uploads/2026/06/CV-AdamLeive.pdf",
                     "Adam Leive", "conditionally accepted"),
    manual_confirmed("Mechanism Design for Personalized Policy: A Field Experiment Incentivizing Exercise",
                     "Econometrica",
                     "https://drive.google.com/file/d/1gr-6G-Y0lYEEGOrpUx8_22D6atHFcfIl/view?usp=drive_link",
                     "Rebecca Dizon-Ross"),
    manual_confirmed("Quantitative Tightening Around the Globe: What Have We Learned?",
                     "Journal of Money, Credit and Banking",
                     "https://www.dropbox.com/scl/fi/evle4568e99ngjs6iinbp/CV_Du_April2026.pdf?rlkey=4ak45jq9di2j7vdpu2hrfss65&dl=0",
                     "Wenxin Du"),
    manual_confirmed("The Class Gap in Career Progression: Evidence from US Academia", "Econometrica",
                     "https://mitsloan.mit.edu/shared/ods/documents?PersonID=101679&DocID=14297",
                     "Anna M. Stansbury", "conditionally accepted"),
    manual_confirmed("The Economic Costs of Rape", "American Economic Review",
                     "https://drive.google.com/file/d/1utJLCkBlRnhAfvuMGK1Z1zq2zV-v_1yg/view?usp=sharing",
                     "Emily E. Nix", "conditionally accepted"),
    manual_confirmed("The Impact of Unions on Wages in the Public Sector: Evidence from Higher Education",
                     "American Economic Review: Insights", "http://korykroft.com/cv/resume_1.pdf",
                     "Kory Kroft"),
    manual_confirmed("The Politicization of Social Responsibility", "Journal of Finance",
                     "http://www.gormley.info/uploads/8/6/8/3/86834336/cv.pdf", "Todd Gormley"),
    manual_confirmed("Trade and the End of Antiquity", "Econometrica",
                     "https://tchaney.github.io/files/CV.pdf", "Thomas Chaney", "accepted"),
    manual_confirmed("Why Do Union Jobs Pay More? New Evidence from Matched Employer-Employee Data",
                     "Quarterly Journal of Economics", "https://www.pierreloupbeauregard.org/",
                     "Pierre-Loup Beauregard", "conditionally accepted"),
    manual_confirmed("Job Search, Wages, and Inflation", "American Economic Review",
                     "https://sites.google.com/site/laurapilossoph/", "Laura Pilossoph",
                     "conditionally accepted"),
    manual_confirmed("Optimal Public Transportation Networks: Evidence from the World's Largest Bus Rapid Transit System in Jakarta",
                     "American Economic Review",
                     "https://economics.mit.edu/sites/default/files/2025-07/250630%20Olken%20CV.pdf",
                     "Benjamin A. Olken", "conditionally accepted"),
    manual_confirmed("Closing the Revolving Door", "Journal of Finance",
                     "https://sites.google.com/site/kairongxiao/", "Kairong Xiao"),
    manual_confirmed("Failures of Contingent Reasoning in Annuitization Decisions", "AEJ: Microeconomics",
                     "http://www.dmitrytaubinsky.com/", "Dmitry Taubinsky", "accepted"),
    manual_confirmed("Identifying Monetary Policy Shocks: A Natural Language Approach", "AEJ: Macroeconomics",
                     "http://econweb.umd.edu/~webspace/aruoba/boragan_aruoba_cv.pdf",
                     "S. Borağan Aruoba"),
    manual_confirmed("Nonbank Fragility in Credit Markets: Evidence from a Two-Layer Asset Demand System",
                     "Journal of Finance", "https://sites.google.com/site/kairongxiao/", "Kairong Xiao"),
    manual_confirmed("Rationing Medicine Through Bureaucracy: Authorization Restrictions in Medicare",
                     "American Economic Review", "https://sites.google.com/site/zarekcb/",
                     "Zarek Brot-Goldberg", "accepted"),
    manual_confirmed("Remote Work and City Structure", "American Economic Review",
                     "https://www.dropbox.com/s/m6x9mcptiw5h2hv/FerdinandoMonte.pdf?raw=1",
                     "Ferdinando Monte"),
    manual_confirmed("Research and/or Development? Financial Frictions and Innovation Investment",
                     "Journal of Finance",
                     "https://www.kellogg.northwestern.edu/faculty/mezzanotti/documents/CV_mezzanotti.pdf",
                     "Filippo Mezzanotti", "accepted"),
    manual_confirmed("Stablecoin Runs and the Centralization of Arbitrage", "Review of Financial Studies",
                     "https://business.columbia.edu/sites/default/files-efs/person/cv/Ma_Yiming_CV_2025.pdf",
                     "Yiming Ma", "accepted"),
    manual_confirmed("Strengthening Fragile States: Evidence from Mobile Salary Payments in Afghanistan",
                     "Review of Economic Studies", "http://www.jblumenstock.com", "Joshua Blumenstock",
                     "accepted"),
    manual_confirmed("The Rise of Alternatives", "Review of Financial Studies",
                     "https://www.emilsiriwardane.com/", "Emil Siriwardane"),
    manual_confirmed("Why is Trade Not Free? A Revealed Preference Approach", "Econometrica",
                     "https://dave-donaldson.com/wp-content/uploads/Donaldson_CV.pdf", "Dave Donaldson",
                     "conditionally accepted"),
])

MANUAL_CONFIRMED.extend([
    manual_confirmed("Automation in Small Business Lending Can Reduce Racial Disparities: Evidence from the Paycheck Protection Program",
                     "Journal of Finance", "http://pages.stern.nyu.edu/~tkuchler/",
                     "Theresa Kuchler", "accepted"),
    manual_confirmed("Cassatts in the Attic", "AEJ: Applied Economics",
                     "https://www.dropbox.com/scl/fi/ojbths84tc0yb64jsc3g5/CV_-Marl-ne-KOFFI.pdf?rlkey=x1r7w08d98hzuvf6vnv9o8j4u&dl=0",
                     "Marlène Koffi", "conditionally accepted"),
    manual_confirmed("College Major Restrictions and Student Stratification", "AEJ: Applied Economics",
                     "https://zacharybleemer.com/", "Zachary Bleemer",
                     "revise and resubmit", status="rr"),
    manual_confirmed("Community Impacts of Mass Incarceration", "Journal of Policy Analysis and Management",
                     "https://evanriehl.github.io/riehl_cv.pdf", "Evan Riehl",
                     "revise and resubmit", status="rr"),
    manual_confirmed("Eclipse of Rent-Sharing: The Effects of Managers’ Business Education on Wages and the Labor Share in the US and Denmark",
                     "American Economic Review", "http://alexxihe.github.io/cv.pdf",
                     "Alex X. He", "conditionally accepted"),
    manual_confirmed("Intermediation via Credit Chains", "Journal of Finance",
                     "https://zhiguohe.net/wp-content/uploads/2026/03/202512-He-CV-Draft-with-courses.pdf",
                     "Zhiguo He"),
    manual_confirmed("Optimal Policy Rules in HANK", "Review of Economic Studies",
                     "https://alisdairmckay.com/", "Alisdair McKay", "accepted"),
    manual_confirmed("Racial Concordance and the Quality of Medical Care: Evidence from the Military",
                     "Review of Economic Studies",
                     "https://economics.mit.edu/sites/default/files/2026-07/Gruber%20Resume%207.7.26.pdf",
                     "Jonathan Gruber"),
    manual_confirmed("Strategic Learning and Corporate Investment", "Journal of Finance",
                     "https://fisher.osu.edu/people/wittry.2", "Michael D. Wittry"),
    manual_confirmed("The Impact of Affirmative Action Litigation on Police Killings of Civilians",
                     "AEJ: Applied Economics", "https://alorte.github.io/",
                     "Alberto Ortega", "accepted"),
    manual_confirmed("The Productivity of Professions: Evidence from the Emergency Department",
                     "American Economic Review",
                     "https://drive.google.com/file/d/1wvG_OMvmlVhyw0iQl75DFAG0QeDLOIgM/view?usp=share_link",
                     "Yiqun Chen"),
    manual_confirmed("The Real Channel for Nominal Bond-Stock Puzzles", "Journal of Finance",
                     "https://www.dropbox.com/scl/fi/iz3l1hlx4zuh3z3litr5u/CV_Lars_Lochstoer_2026.pdf?rlkey=h3dq96l8uksygtrs4j8xkkrgx&dl=0",
                     "Lars A. Lochstoer"),
    manual_confirmed("The Regressive Nature of the U.S. Tariff Code: Origins and Implications",
                     "Quarterly Journal of Economics", "https://coxlydia.com/Cox_CV.pdf",
                     "Lydia Cox", "conditionally accepted"),
    manual_confirmed("Estimating the Economic Value of Zoning Reform", "AEJ: Economic Policy",
                     "https://faculty.wharton.upenn.edu/wp-content/uploads/2016/11/cv_fernando_ferreira-12.pdf",
                     "Fernando V. Ferreira", "conditionally accepted"),
    manual_confirmed("How Resilient is Mortgage Credit Supply? Evidence from the COVID-19 Pandemic",
                     "Journal of Finance",
                     "https://www.philadelphiafed.org/-/media/FRBP/Assets/People/Curricula-Vitae/vita_lambie-hanson.pdf",
                     "Lauren Lambie-Hanson"),
    {
        "normalized_title": norm("The Psychosocial Value of Employment"),
        "title": "The Psychosocial Value of Employment",
        "status": "published",
        "journal": "American Economic Review",
        "pub_year": 2022,
        "evidence_url": "https://www.erinmunrokelley.com/s/ErinKelley_CV2026.pdf",
        "evidence_author": "Erin M. Kelley",
        "evidence_phrase": "published",
        "reviewed_at": "2026-07-14",
    },
    manual_confirmed("Why Are the Wealthiest So Wealthy?", "Econometrica",
                     "https://joachimhubmer.github.io/assets/CV_Joachim_Hubmer.pdf",
                     "Joachim Hubmer"),
    manual_confirmed("Feedback and Contagion through Distressed Competition", "Journal of Finance",
                     "http://www.mit.edu/~huichen/", "Hui Chen"),
    manual_confirmed("Scaling Up Agricultural Policy Interventions: Theory and Evidence from Uganda",
                     "Econometrica",
                     "https://www.dropbox.com/scl/fi/2sbtx8ea8kagaathmer66/Lauren_Falcao_Bergquist_CV.pdf?rlkey=8mshrzifbhth7yx4hc7mitas7&e=1&dl=0",
                     "Lauren F. Bergquist", "conditionally accepted"),
    manual_confirmed("Taxation and Supplier Networks: Evidence from India", "AEJ: Applied Economics",
                     "https://drive.google.com/file/d/1dDWnShfXK6_T8Me01CwUO6yI7M-x95Ov/view?usp=sharing",
                     "Lucie Gadenne", "conditionally accepted"),
    manual_confirmed("Liquidity Constraints and the Value of Insurance", "AEJ: Microeconomics",
                     "https://sites.google.com/a/wisc.edu/jrsydnor/", "Justin R. Sydnor"),
    manual_confirmed("Physician Behavior in the Presence of a Secondary Market: The Case of Prescription Opioids",
                     "Econometrica", "http://mollyschnell.com/s/Schnell_CV_052026.pdf",
                     "Molly Schnell"),
    manual_confirmed("Uncertainty and Change: Survey Evidence of Firms' Subjective Beliefs",
                     "American Economic Review", "http://www.stanford.edu/~schneidr/",
                     "Martin Schneider", "conditionally accepted"),
    manual_confirmed("The Spillover Effects of Top Income Inequality", "Econometrica",
                     "http://www.gottlieb.ca/", "Joshua D. Gottlieb", "conditionally accepted"),
    manual_confirmed("Are CEOs Different? Characteristics of Top Managers", "Journal of Finance",
                     "https://www.chicagobooth.edu/faculty/directory/k/steven-neil-kaplan",
                     "Steven N. Kaplan"),
    manual_confirmed("Earnings Dynamics and Firm-Level Shocks", "Journal of Labor Economics",
                     "https://economics.yale.edu/sites/default/files/cv/Costas_Meghir_CV.pdf",
                     "Costas Meghir"),
    manual_confirmed("Two-sided Search in International Markets", "Journal of Political Economy",
                     "https://www.danielyixu.com/", "Daniel Xu", "accepted"),
    manual_confirmed("Fundamentally, Momentum is Fundamental Momentum", "Journal of Financial Economics",
                     "https://mysimon.rochester.edu/novy-marx/research/CV.pdf",
                     "Robert Novy-Marx", "revise and resubmit", status="rr"),
    manual_confirmed("Police Patrols and Crime", "Economic Journal",
                     "https://sites.google.com/site/giovannimastrobuoni/",
                     "Giovanni Mastrobuoni", "R&R", status="rr"),
    manual_confirmed("Environmental Catastrophe and the Direction of Invention: Evidence from the American Dust Bowl",
                     "Review of Economics and Statistics",
                     "https://economics.mit.edu/sites/default/files/2026-06/MosconaCV_latest_website_0.pdf",
                     "Jacob Moscona", "conditionally accepted"),
    manual_confirmed("Inappropriate Technology: Evidence from Global Agriculture",
                     "American Economic Review",
                     "https://economics.mit.edu/sites/default/files/2026-06/MosconaCV_latest_website_0.pdf",
                     "Jacob Moscona", "conditionally accepted"),
    manual_confirmed("A Quantity-Based Approach to Constructing Climate Risk Hedge Portfolios",
                     "Journal of Finance",
                     "https://stefanogiglio.org/papers/giglio-cv.pdf",
                     "Stefano Giglio"),
    manual_confirmed("Dementia and Long-run Trajectories in Household Finances",
                     "AEJ: Economic Policy",
                     "https://economics.ucla.edu/wp-content/uploads/2016/09/year25c.pdf",
                     "Kathleen M. McGarry"),
    manual_confirmed("Discrimination and State Capacity: Evidence from WWII U.S. Army Enlistment",
                     "Review of Economic Studies",
                     "https://faculty.kellogg.northwestern.edu/fac_cv_download.php?fac_id=12681",
                     "Nancy Qian"),
])


def main():
    candidates = json.loads((ROOT / "nber_si" / "data" / "cv_audit_candidates.json").read_text())
    grouped = defaultdict(list)
    for row in candidates:
        grouped[norm(row["title"])].append(row)

    audit_path = ROOT / "nber_si" / "data" / "cv_audit.json"
    existing = json.loads(audit_path.read_text()) if audit_path.exists() else []
    confirmed_by_title = {row["normalized_title"]: row for row in existing}
    manual_confirmed_titles = {row["normalized_title"] for row in MANUAL_CONFIRMED}
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
        if title_key in manual_confirmed_titles:
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
