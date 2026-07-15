import json
import re
import unittest
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROWS = json.loads((ROOT / "nber_si" / "data" / "papers_enriched.json").read_text())


class NberSummerInstituteDataTest(unittest.TestCase):
    def test_row_integrity(self):
        self.assertEqual(len(ROWS), 6990)
        self.assertEqual(len({row["id"] for row in ROWS}), len(ROWS))
        self.assertTrue(all(row.get("title") and row.get("agenda_authors") for row in ROWS))
        self.assertTrue(all(row["status"] in {"working_paper", "rr", "published"} for row in ROWS))
        self.assertTrue(all(row.get("journal") for row in ROWS if row["status"] == "rr"))
        self.assertTrue(all(not row.get("journal") for row in ROWS if row["status"] == "working_paper"))

    def test_display_text_is_normalized(self):
        self.assertFalse(any(re.search(r"<[^>]+>", row["agenda_authors"]) for row in ROWS))
        self.assertFalse(any("&amp;" in (row.get("journal") or "") for row in ROWS))
        self.assertFalse(any(re.search(r"<[^>]+>|[\x00-\x08\x0b\x0c\x0e-\x1f]",
                                       row.get("published_title") or "") for row in ROWS))

    def test_evidence_tiers_are_internally_consistent(self):
        allowed = {
            "multiple_authors_cross_checked", "cross_checked_prior_research",
            "cross_checked_renamed_lineage", "cross_checked_author_source",
            "author_page_checked_no_named_status",
            "official_nber_published", "automated_crossref", "provisional",
        }
        self.assertTrue(all(row["verification"] in allowed for row in ROWS))
        for row in ROWS:
            if row["verification"] == "multiple_authors_cross_checked":
                authors = {author.casefold() for author in row.get("evidence_authors") or []}
                self.assertGreaterEqual(len(authors), 2, row["id"])

    def test_known_false_negatives_are_corrected(self):
        by_title = {}
        for row in ROWS:
            by_title.setdefault(row["title"], []).append(row)
        for title, journal in {
            "How Do Firms Respond to Unions?": "Quarterly Journal of Economics",
            "A Theory of Economic Coercion and Fragmentation": "Journal of Political Economy",
            "The Financial Consequences of Being Denied Benefit Access": "AEJ: Economic Policy",
            "Estimating Counterfactual Matrix Means with Short Panel Data": "Econometrica",
            "The Dynamics of Deposit Flightiness and its Impact on Financial Stability": "Review of Financial Studies",
            "Earnings Instability": "Quarterly Journal of Economics",
            "College Major Restrictions and Student Stratification": "AEJ: Applied Economics",
            "Fundamentally, Momentum is Fundamental Momentum": "Journal of Financial Economics",
            "Police Patrols and Crime": "Economic Journal",
        }.items():
            matches = by_title[title]
            self.assertTrue(all(row["status"] == "rr" and row["journal"] == journal for row in matches))
        tenuous = by_title["The Tenuous Attachments of Working Class Men"]
        self.assertTrue(all(row["status"] == "published" and row["pub_year"] == 2019 for row in tenuous))
        for title in {
            "Antidepressant Treatment in Childhood",
            "Beyond the War: Public Service and the Transmission of Gender Norms",
            "Inelastic Demand at the Extensive and Intensive Margins",
        }:
            self.assertTrue(all(row["status"] == "working_paper" for row in by_title[title]))

    def test_second_pass_publication_matches_are_retained(self):
        by_title = {}
        for row in ROWS:
            by_title.setdefault(row["title"], []).append(row)
        expected = {
            "The Macroeconomic Effects of Government Asset Purchases: Evidence from Postwar US Housing Credit Policy":
                ("Quarterly Journal of Economics", 2018),
            "Drilling Like There's No Tomorrow: Bankruptcy, Insurance, and Environmental Risk":
                ("American Economic Review", 2019),
            "New Frontiers: The Origins and Content of New Work, 1940-2018":
                ("Quarterly Journal of Economics", 2024),
            "Effects of Copyrights on Science: Evidence from the World War II Book Republication Program":
                ("AEJ: Microeconomics", 2021),
            "How Does Unemployment Affect Consumer Spending?":
                ("American Economic Review", 2019),
            "Training Aspiring Entrepreneurs to Pitch Experienced Investors: Evidence from a Field Experiment":
                ("Management Science", 2018),
            "From Final Goods to Inputs: The Protectionist Effect of Preferential Rules of Origin":
                ("American Economic Review", 2018),
            "The Effects of Foreign MNEs on Workers and Firms in the United States":
                ("Quarterly Journal of Economics", 2021),
            "The Long-Run Effects of Residential Racial Desegregation Programs: Evidence from Gautreaux":
                ("Quarterly Journal of Economics", 2025),
            "LinkedOut! Discrimination in Job Network Formation":
                ("Quarterly Journal of Economics", 2025),
            "Does Incomplete Spanning in International Financial Markets Help to Understand Exchange Rates?":
                ("American Economic Review", 2019),
            "Why do Workers Dislike Inflation? Wage Erosion and Conflict Costs":
                ("Econometrica", None),
            "Fiscal Policy in a Networked Economy":
                ("AEJ: Macroeconomics", None),
            "How Small is Small? Non-linearities in Heterogeneous Agent Models":
                ("Journal of Economic Theory", None),
            "The Long-run Effect of Air Pollution on Survival":
                ("American Economic Review", None),
            "College as a Marriage Market":
                ("Review of Economic Studies", None),
            "Mechanism Design for Personalized Policy: A Field Experiment Incentivizing Exercise":
                ("Econometrica", None),
            "The Labor Market Returns to Delaying Pregnancy":
                ("American Economic Review", None),
            "Community Engagement and Public Safety: Evidence from Crime Enforcement Targeting Immigrants":
                ("American Economic Review", None),
            "Trade and the End of Antiquity":
                ("Econometrica", None),
            "Why Do Union Jobs Pay More? New Evidence from Matched Employer-Employee Data":
                ("Quarterly Journal of Economics", None),
            "Stablecoin Runs and the Centralization of Arbitrage":
                ("Review of Financial Studies", None),
            "Deadwood Labor? The Effects of Eliminating Employment Protection for Older Workers":
                ("AEJ: Applied Economics", None),
            "Quantitative Tightening Around the Globe: What Have We Learned?":
                ("Journal of Money, Credit and Banking", None),
            "Automation in Small Business Lending Can Reduce Racial Disparities: Evidence from the Paycheck Protection Program":
                ("Journal of Finance", None),
            "Cassatts in the Attic":
                ("AEJ: Applied Economics", None),
            "The Psychosocial Value of Employment":
                ("American Economic Review", 2022),
            "Why Are the Wealthiest So Wealthy?":
                ("Econometrica", None),
            "Two-sided Search in International Markets":
                ("Journal of Political Economy", None),
            "Environmental Catastrophe and the Direction of Invention: Evidence from the American Dust Bowl":
                ("Review of Economics and Statistics", None),
            "Inappropriate Technology: Evidence from Global Agriculture":
                ("American Economic Review", None),
            "A Quantity-Based Approach to Constructing Climate Risk Hedge Portfolios":
                ("Journal of Finance", None),
            "Dementia and Long-run Trajectories in Household Finances":
                ("AEJ: Economic Policy", None),
            "Discrimination and State Capacity: Evidence from WWII U.S. Army Enlistment":
                ("Review of Economic Studies", None),
        }
        for title, (journal, year) in expected.items():
            matches = by_title[title]
            self.assertTrue(all(row["status"] == "published" for row in matches), title)
            self.assertTrue(all(row["journal"] == journal for row in matches), title)
            if year is not None:
                self.assertTrue(all(row["pub_year"] == year for row in matches), title)

    def test_adjacent_project_statuses_stay_rejected(self):
        by_title = {}
        for row in ROWS:
            by_title.setdefault(row["title"], []).append(row)
        for title in {
            "Labor Market Fluidity, On-the-Job Learning, and Career Growth Across Countries",
            "Longevity and Occupational Choice",
            "Structural Reinforcement Learning for Heterogeneous Agent Macroeconomics",
            "The Great Game: A Model of Geoeconomic Competition",
            "The Price and Distributional Impact of Flood Risk Disclosure: Evidence from US Housing Platforms",
            "What Do $40 Trillion of Portfolio Holdings Say about Monetary Policy Transmission?",
        }:
            self.assertTrue(all(row["status"] == "working_paper" for row in by_title[title]), title)

    def test_official_publications_have_years(self):
        self.assertFalse(any(row["verification"] == "official_nber_published" and not row.get("pub_year")
                             for row in ROWS))

    def test_snapshot_counts(self):
        self.assertEqual(Counter(row["status"] for row in ROWS),
                         {"working_paper": 4257, "published": 2491, "rr": 242})

    def test_repeated_exact_title_author_lineages_are_consistent(self):
        by_title = {}
        for row in ROWS:
            by_title.setdefault(row["title"], []).append(row)
        for title, matches in by_title.items():
            if len(matches) < 2:
                continue
            author_sets = [{name.casefold() for name in row.get("authors_list") or []} for row in matches]
            if len({tuple(sorted(authors)) for authors in author_sets}) == 1:
                outcomes = {(row["status"], row.get("journal"), row.get("pub_year")) for row in matches}
                self.assertEqual(len(outcomes), 1, title)

    def test_csv_array_fields_are_json(self):
        with (ROOT / "nber_si" / "data" / "papers_enriched.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        example = next(row for row in rows if row["evidence_authors"])
        self.assertIsInstance(json.loads(example["evidence_authors"]), list)
        self.assertIsInstance(json.loads(example["evidence_urls"]), list)


class NberSummerInstituteDashboardTest(unittest.TestCase):
    @staticmethod
    def dashboard_rows(page):
        match = re.search(r"const RAW_DATA = (\[.*?\]);\nconst AGGREGATE_ALL", page, re.S)
        if not match:
            raise AssertionError("Could not find embedded dashboard data")
        return json.loads(match.group(1))

    def test_generated_mirrors_match(self):
        local = (ROOT / "nber_si" / "dashboard" / "index.html").read_text()
        public = (ROOT / "docs" / "nber-si" / "index.html").read_text()
        self.assertEqual(local, public)
        embedded = self.dashboard_rows(local)
        self.assertEqual(len(embedded), len(ROWS))
        self.assertEqual(Counter(row["status"] for row in embedded),
                         Counter(row["status"] for row in ROWS))

    def test_all_program_view_is_aggregate(self):
        page = (ROOT / "nber_si" / "dashboard" / "index.html").read_text()
        self.assertIn("const AGGREGATE_ALL = true;", page)
        self.assertNotIn('$("#f-conf").value = "Industrial Organization"', page)
        self.assertIn("Each bar sums paper appearances across all programs", page)
        self.assertIn("const roomy = !comparisonSelection() && confs.length <= 1;", page)
        self.assertEqual(page.count("chartGeometry(confs)"), 3)
        self.assertIn("function niceAxis(maxValue)", page)
        self.assertEqual(page.count("niceAxis(maxN)"), 2)
        self.assertNotIn("maxN > 10 ? 5 : 2", page)

    def test_evidence_and_year_controls_are_wired(self):
        page = (ROOT / "nber_si" / "dashboard" / "index.html").read_text()
        self.assertIn("What do the evidence levels mean?", page)
        self.assertIn("Unresolved — no matched author evidence", page)
        self.assertIn("Cross-checked renamed lineage", page)
        self.assertNotIn("author audit pending", page)
        self.assertIn("rows with matched evidence", page)
        self.assertNotIn("rows with non-provisional evidence", page)
        self.assertIn("Evidence:</b>", page)
        self.assertIn('const selected = Number($("#f-year").value);', page)


if __name__ == "__main__":
    unittest.main()
