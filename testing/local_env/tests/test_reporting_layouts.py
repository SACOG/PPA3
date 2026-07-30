import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, layout_loader

LOCAL_ATP_RUN = os.path.join(
    os.path.dirname(HERE), "out", "runs", "20260729_172109", "merged.json"
)


def _load_local_merged():
    with open(LOCAL_ATP_RUN, encoding="utf-8") as f:
        return json.load(f)


@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestVmtLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpVMT")
        self.data = _load_local_merged()["RPArtExpVMT"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)
        self.assertEqual(self.layout["service"], "RPArtExpVMT")

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [], f"cards with no data: {missing}")

    def test_three_charts_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        subtitles = [c["subtitle"] for c in section["cards"]]
        self.assertEqual(subtitles, [
            "Jobs and Houses nearby by 2035",
            "Walk/bike destinations nearby (land use by 2035)*",
            "Walk/bike destinations nearby (mode share)*",
        ])


@unittest.skipUnless(os.path.isfile(LOCAL_ATP_RUN), "local ATP harness run not present")
class TestSafetyLayout(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpSafety")
        self.data = _load_local_merged()["RPArtExpSafety"]

    def test_layout_loads(self):
        self.assertIsNotNone(self.layout)

    def test_no_card_reports_missing_against_real_local_data(self):
        section = cards.build_section(self.layout, self.data)
        missing = [c for c in section["cards"] if c["missing"]]
        self.assertEqual(missing, [])

    def test_task5_only_charts_excluded(self):
        # Collision Types / Primary Collision Factors are Task-5 branch-only additions,
        # confirmed absent from the real prod capture (Task 11) and the golden PDF.
        chart_sources = [c.get("source_chart") for c in self.layout["cards"] if c["type"] == "chart"]
        self.assertNotIn("Collision Types", chart_sources)
        self.assertNotIn("Primary Collision Factors", chart_sources)

    def test_five_cards_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual([c["type"] for c in section["cards"]], ["kpi", "image", "table", "chart", "table"])


if __name__ == "__main__":
    unittest.main()
