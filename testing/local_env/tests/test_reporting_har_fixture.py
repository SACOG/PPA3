import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, layout_loader

FIXTURE_DIR = os.path.join(HERE, "fixtures", "reporting", "har_prod_capture")

# The 5 services the ATP path dispatches -- the only ones with a layout config as of this plan.
ATP_SERVICES = [
    "RPArtExpVMT",
    "RPArtExpSafety",
    "RPArtExpMultiModal",
    "RPArtExpEconProsp",
    "RPArtSGRSGR",
]


def _load_merged():
    with open(os.path.join(FIXTURE_DIR, "merged.json"), encoding="utf-8") as f:
        return json.load(f)


class TestHarFixtureExists(unittest.TestCase):
    def test_fixture_files_present(self):
        self.assertTrue(os.path.isfile(os.path.join(FIXTURE_DIR, "manifest.json")))
        self.assertTrue(os.path.isfile(os.path.join(FIXTURE_DIR, "merged.json")))

    def test_fixture_is_a_different_project_than_either_golden(self):
        with open(os.path.join(FIXTURE_DIR, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        name = manifest["inputs"]["project_name"]
        self.assertNotIn(name, ("Trell Test", "Active Transportation Program Report Test"))


class TestLayoutConfigsAgainstRealProdCapture(unittest.TestCase):
    """Every card in every ATP layout config must resolve against this REAL prod-captured
    payload -- not just our own local harness's merged.json. This is the structural check
    that replaces the design's original (infeasible) numeric golden-value comparison."""

    def setUp(self):
        self.merged = _load_merged()

    def test_no_missing_fields_in_any_atp_service(self):
        problems = []
        for service in ATP_SERVICES:
            layout = layout_loader.load_layout(service)
            self.assertIsNotNone(layout, f"{service}: no layout config")
            section = cards.build_section(layout, self.merged[service])
            for card in section["cards"]:
                if card["missing"]:
                    problems.append((service, card.get("subtitle")))
        self.assertEqual(problems, [], f"cards with no data against the real prod capture: {problems}")


# Fix 4 (final whole-branch review, 2026-07-30): these order/subtitle/sub_outcome/exclusion
# checks used to live ONLY in test_reporting_layouts.py, gated behind
# @unittest.skipUnless(os.path.isdir(LOCAL_ATP_RUN_DIR), ...) against the gitignored local
# harness run at testing/local_env/out/runs/20260729_172109 -- so on a fresh clone or CI
# runner, all of them silently skip green with no assertion ever running. They're duplicated
# here (ungated) against the committed HAR-derived fixture so the same fidelity properties are
# verified on every machine. test_reporting_layouts.py's gated classes are left in place --
# they still add value on this machine by checking against a second, different real dataset.
class TestVmtLayoutAgainstHarFixture(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpVMT")
        self.data = _load_merged()["RPArtExpVMT"]

    def test_three_charts_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        subtitles = [c["subtitle"] for c in section["cards"]]
        self.assertEqual(subtitles, [
            "Jobs and Houses nearby by 2035",
            "Walk/bike destinations nearby (land use by 2035)*",
            "Walk/bike destinations nearby (mode share)*",
        ])


class TestSafetyLayoutAgainstHarFixture(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpSafety")
        self.data = _load_merged()["RPArtExpSafety"]

    def test_five_cards_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual([c["type"] for c in section["cards"]], ["kpi", "image", "table", "chart", "table"])

    def test_task5_only_charts_excluded(self):
        # Collision Types / Primary Collision Factors are Task-5 branch-only additions,
        # confirmed absent from the real prod capture (Task 11) and the golden PDF.
        chart_sources = [c.get("source_chart") for c in self.layout["cards"] if c["type"] == "chart"]
        self.assertNotIn("Collision Types", chart_sources)
        self.assertNotIn("Primary Collision Factors", chart_sources)


class TestMultiModalLayoutAgainstHarFixture(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpMultiModal")
        self.data = _load_merged()["RPArtExpMultiModal"]

    def test_six_cards_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual(
            [c["type"] for c in section["cards"]],
            ["table", "table", "image", "table", "image", "chart"],
        )


class TestEconProspLayoutAgainstHarFixture(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtExpEconProsp")
        self.data = _load_merged()["RPArtExpEconProsp"]

    def test_sub_outcomes_present_in_golden_order(self):
        section = cards.build_section(self.layout, self.data)
        sub_outcomes = [c["sub_outcome"] for c in section["cards"] if c.get("sub_outcome")]
        self.assertEqual(sub_outcomes, [
            "Sub outcome: Increase Job Access",
            "Sub outcome: Increase School Access",
            "Sub outcome: Support Ag Economy",
        ])


class TestSgrLayoutAgainstHarFixture(unittest.TestCase):
    def setUp(self):
        self.layout = layout_loader.load_layout("RPArtSGRSGR")
        self.data = _load_merged()["RPArtSGRSGR"]

    def test_three_kpi_cards(self):
        section = cards.build_section(self.layout, self.data)
        self.assertEqual([c["type"] for c in section["cards"]], ["kpi", "kpi", "kpi"])


if __name__ == "__main__":
    unittest.main()
