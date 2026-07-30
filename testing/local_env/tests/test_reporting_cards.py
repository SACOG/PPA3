import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards


class TestFormatValue(unittest.TestCase):
    def test_percent_formats_fraction(self):
        self.assertEqual(cards._format_value(0.3333, "percent"), "33.3%")

    def test_number_formats_float_two_decimals(self):
        self.assertEqual(cards._format_value(74.91748017650224, "number"), "74.92")

    def test_number_formats_int_with_commas(self):
        self.assertEqual(cards._format_value(15000, "number"), "15,000")

    def test_string_value_passes_through(self):
        self.assertEqual(cards._format_value("0", "number"), "0")

    def test_none_is_no_data(self):
        self.assertEqual(cards._format_value(None, "number"), "(no data)")


class TestBuildKpiCard(unittest.TestCase):
    def test_present_value(self):
        cfg = {"source": "Total collisions", "subtitle": "Total Collisions", "question": "Q?"}
        data = {"Total collisions": 12}
        card = cards.build_kpi_card(cfg, data)
        self.assertEqual(card["type"], "kpi")
        self.assertFalse(card["missing"])
        self.assertEqual(card["value_display"], "12")
        self.assertEqual(card["subtitle"], "Total Collisions")
        self.assertEqual(card["question"], "Q?")

    def test_missing_value_flagged(self):
        cfg = {"source": "Not There"}
        card = cards.build_kpi_card(cfg, {})
        self.assertTrue(card["missing"])
        self.assertEqual(card["value_display"], "(no data)")


class TestBuildTableCard(unittest.TestCase):
    def test_rows_built_in_row_labels_order(self):
        cfg = {
            "source": "Collisions per 100 million VMT",
            "row_labels": {
                "Project": "On project segment*",
                "Community Type": "Within community type",
                "Region": "Within region",
            },
        }
        data = {"Collisions per 100 million VMT": {"Project": -1.0, "Community Type": 140.4, "Region": 95.4}}
        card = cards.build_table_card(cfg, data)
        self.assertFalse(card["missing"])
        self.assertEqual(
            [r["label"] for r in card["rows"]],
            ["On project segment*", "Within community type", "Within region"],
        )
        self.assertEqual(card["rows"][0]["value_display"], "-1.00")

    def test_missing_source_flagged_no_rows(self):
        cfg = {"source": "Nope", "row_labels": {"Project": "Project"}}
        card = cards.build_table_card(cfg, {})
        self.assertTrue(card["missing"])
        self.assertEqual(card["rows"], [])

    def test_percent_format(self):
        cfg = {
            "source": "Bike lanes and paths as share of total road miles",
            "row_labels": {"Within 0.25mi": "Within 0.25mi of project"},
            "value_format": "percent",
        }
        data = {"Bike lanes and paths as share of total road miles": {"Within 0.25mi": 0.44}}
        card = cards.build_table_card(cfg, data)
        self.assertEqual(card["rows"][0]["value_display"], "44.0%")


class TestBuildChartCard(unittest.TestCase):
    def test_categories_and_series_extracted_in_feature_order(self):
        cfg = {
            "source_chart": "Jobs and Dwelling",
            "x_field": "year",
            "series": [{"field": "jobs", "label": "Jobs"}, {"field": "dwellingUnits", "label": "Dwelling Units"}],
        }
        data = {
            "charts": {
                "Jobs and Dwelling": {
                    "title": "t",
                    "features": [
                        {"attributes": {"year": "2020", "jobs": 1612, "dwellingUnits": 3147}},
                        {"attributes": {"year": "2035", "jobs": 2303, "dwellingUnits": 4516}},
                    ],
                }
            }
        }
        card = cards.build_chart_card(cfg, data)
        self.assertFalse(card["missing"])
        spec = json.loads(card["chart_json"])
        self.assertEqual(spec["categories"], ["2020", "2035"])
        self.assertEqual(spec["series"][0], {"label": "Jobs", "data": [1612, 2303]})
        self.assertEqual(spec["series"][1], {"label": "Dwelling Units", "data": [3147, 4516]})

    def test_missing_chart_flagged(self):
        cfg = {"source_chart": "Nope", "x_field": "year", "series": [{"field": "jobs", "label": "Jobs"}]}
        card = cards.build_chart_card(cfg, {"charts": {}})
        self.assertTrue(card["missing"])
        spec = json.loads(card["chart_json"])
        self.assertEqual(spec["categories"], [])


class TestBuildImageCard(unittest.TestCase):
    def test_null_url_is_not_missing(self):
        # A present-but-null Image Url (the normal local case, no .aprx staged) must NOT be
        # flagged "missing" -- that would falsely fail every image card in every local run.
        card = cards.build_image_card({"source": "Bikeway Image Url", "caption": "Bikeway Map"}, {"Bikeway Image Url": None})
        self.assertIsNone(card["url"])
        self.assertFalse(card["missing"])
        self.assertEqual(card["caption"], "Bikeway Map")

    def test_real_url_passthrough(self):
        card = cards.build_image_card({"source": "Bikeway Image Url"}, {"Bikeway Image Url": "https://example/x.png"})
        self.assertEqual(card["url"], "https://example/x.png")
        self.assertFalse(card["missing"])

    def test_structurally_absent_field_is_missing(self):
        card = cards.build_image_card({"source": "Bikeway Image Url"}, {})
        self.assertTrue(card["missing"])


class TestBuildCardDispatch(unittest.TestCase):
    def test_dispatches_by_type(self):
        card = cards.build_card({"type": "kpi", "source": "ADT"}, {"ADT": 15000})
        self.assertEqual(card["type"], "kpi")


class TestBuildSection(unittest.TestCase):
    def test_builds_section_with_cards_in_order(self):
        layout = {
            "service": "RPArtSGRSGR",
            "section_title": "Maintain State of Good Repair",
            "cards": [
                {"type": "kpi", "source": "Pavement Condition Index", "subtitle": "PCI"},
                {"type": "kpi", "source": "ADT", "subtitle": "ADT"},
            ],
        }
        data = {"Pavement Condition Index": 70, "ADT": 15000}
        section = cards.build_section(layout, data)
        self.assertEqual(section["service"], "RPArtSGRSGR")
        self.assertFalse(section["unavailable"])
        self.assertEqual([c["subtitle"] for c in section["cards"]], ["PCI", "ADT"])


if __name__ == "__main__":
    unittest.main()
