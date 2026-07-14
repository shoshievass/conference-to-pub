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
            "cross_checked_author_source", "author_page_checked_no_named_status",
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

    def test_official_publications_have_years(self):
        self.assertFalse(any(row["verification"] == "official_nber_published" and not row.get("pub_year")
                             for row in ROWS))

    def test_snapshot_counts(self):
        self.assertEqual(Counter(row["status"] for row in ROWS),
                         {"working_paper": 4741, "published": 2017, "rr": 232})

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
        self.assertIn("Evidence:</b>", page)
        self.assertIn('const selected = Number($("#f-year").value);', page)


if __name__ == "__main__":
    unittest.main()
