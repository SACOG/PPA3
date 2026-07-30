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


if __name__ == "__main__":
    unittest.main()
