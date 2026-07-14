import csv
import glob
import json
import re
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROWS = json.loads((ROOT / "data" / "papers_enriched.json").read_text())


def normalized_title(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


class IoConferenceDataTest(unittest.TestCase):
    def test_snapshot_and_row_integrity(self):
        self.assertEqual(len(ROWS), 774)
        self.assertEqual(len({row["id"] for row in ROWS}), len(ROWS))
        self.assertEqual(Counter(row["status"] for row in ROWS),
                         {"published": 486, "rr": 90, "working_paper": 198})
        self.assertTrue(all(row.get("title") and row.get("agenda_authors") for row in ROWS))
        self.assertTrue(all(row.get("note") for row in ROWS))
        self.assertTrue(all(row["status"] in {"published", "rr", "working_paper"}
                            for row in ROWS))

    def test_status_fields_are_consistent(self):
        for row in ROWS:
            if row["status"] == "published":
                self.assertTrue(row.get("journal") and row.get("url"), row["id"])
                if row.get("pub_year") is None:
                    self.assertRegex(row["note"].casefold(),
                                     r"accepted|forthcoming|advance|online|issue|conditionally")
            elif row["status"] == "rr":
                self.assertTrue(row.get("journal") and row.get("url"), row["id"])
                self.assertIsNone(row.get("pub_year"), row["id"])
                self.assertIsNone(row.get("lag"), row["id"])
            else:
                self.assertIsNone(row.get("journal"), row["id"])
                self.assertIsNone(row.get("pub_year"), row["id"])
                self.assertIsNone(row.get("lag"), row["id"])

    def test_publication_lags_use_issue_year(self):
        for row in ROWS:
            if row["status"] == "published" and row.get("pub_year") is not None:
                self.assertEqual(row["lag"], row["pub_year"] - row["year"], row["id"])
        by_id = {row["id"]: row for row in ROWS}
        self.assertEqual(by_id["ftc2015-03"]["pub_year"], 2020)
        self.assertEqual(by_id["nber2016-07"]["pub_year"], 2020)

    def test_repeated_titles_have_consistent_outcomes(self):
        for field in ("title", "published_title"):
            groups = defaultdict(list)
            for row in ROWS:
                key = normalized_title(row.get(field))
                if key:
                    groups[key].append(row)
            for key, group in groups.items():
                if len(group) < 2:
                    continue
                outcomes = {(row["status"], row.get("journal"), row.get("pub_year"))
                            for row in group}
                self.assertEqual(len(outcomes), 1, f"{field}: {key}")

    def test_text_is_normalized(self):
        for row in ROWS:
            self.assertNotRegex(row.get("agenda_authors") or "", r"<[^>]+>")
            self.assertNotRegex(row.get("published_title") or "",
                                r"<[^>]+>|[\x00-\x08\x0b\x0c\x0e-\x1f]")
            self.assertNotIn("&amp;", row.get("journal") or "")

    def test_lookup_and_csv_coverage(self):
        lookup_ids = []
        for filename in sorted(glob.glob(str(ROOT / "data" / "lookups" / "batch-*.json"))):
            lookup_ids.extend(row["id"] for row in json.loads(Path(filename).read_text()))
        self.assertEqual(len(lookup_ids), 774)
        self.assertEqual(len(set(lookup_ids)), 774)
        with (ROOT / "data" / "papers_enriched.csv").open(newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        self.assertEqual(len(csv_rows), len(ROWS))
        self.assertEqual({row["id"] for row in csv_rows}, {row["id"] for row in ROWS})


class IoConferenceDashboardTest(unittest.TestCase):
    @staticmethod
    def embedded_rows(page):
        match = re.search(r"const RAW_DATA = (\[.*?\]);\nconst AGGREGATE_ALL", page, re.S)
        if not match:
            raise AssertionError("Could not find embedded dashboard data")
        return json.loads(match.group(1))

    def test_public_io_mirror_matches_local_dashboard(self):
        local = (ROOT / "dashboard" / "index.html").read_text()
        public = (ROOT / "docs" / "io" / "index.html").read_text()
        self.assertEqual(local, public)
        embedded = self.embedded_rows(public)
        self.assertEqual(len(embedded), len(ROWS))
        self.assertEqual(Counter(row["status"] for row in embedded),
                         Counter(row["status"] for row in ROWS))

    def test_public_routes_are_separate(self):
        landing = (ROOT / "docs" / "index.html").read_text()
        nber = (ROOT / "docs" / "nber-si" / "index.html").read_text()
        self.assertIn('href="io/"', landing)
        self.assertIn('href="nber-si/"', landing)
        self.assertNotIn("const RAW_DATA", landing)
        self.assertNotIn("IO conference dashboard", nber)

    def test_shared_dashboard_fixes_apply_to_io(self):
        page = (ROOT / "docs" / "io" / "index.html").read_text()
        self.assertIn("const AGGREGATE_ALL = false;", page)
        self.assertIn('const selected = Number($("#f-year").value);', page)
        self.assertIn("lags.length / 2 - 1", page)
        self.assertIn("const minLag = Math.min(...lags)", page)
        self.assertIn("const sharedMax = Math.max", page)
        self.assertIn("comparison-chart-grid", page)


if __name__ == "__main__":
    unittest.main()
