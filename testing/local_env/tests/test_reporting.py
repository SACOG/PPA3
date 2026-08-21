import os
import sys
import tempfile
import unittest
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "reporting"))
sys.path.insert(0, os.path.dirname(HERE))
import render
import dispatch


class TestReportFallbacks(unittest.TestCase):
    def test_success_without_layout_keeps_summary_and_complete_json(self):
        sections = render.build_sections(
            {"services": [{"service": "UnknownService", "outcome": "Useful outcome", "status": "ok"}]},
            {"UnknownService": {"Score": 12.5, "Rows": [1, 2]}},
        )
        self.assertTrue(sections[0]["generic"])
        self.assertFalse(sections[0]["unavailable"])
        self.assertIn('"Score": 12.5', sections[0]["raw_json"])
        self.assertEqual(sections[0]["summary_rows"][1]["value_display"], "List (2 items)")

    def test_failed_service_explains_its_error(self):
        sections = render.build_sections(
            {"services": [{"service": "Broken", "outcome": "Safety", "status": "failed",
                            "error": "field pop_pov200 is missing"}]},
            {},
        )
        self.assertTrue(sections[0]["unavailable"])
        self.assertIn("pop_pov200", sections[0]["unavailable_reason"])

    def test_malformed_specialized_result_falls_back_instead_of_disappearing(self):
        sections = render.build_sections(
            {"services": [{"service": "RPArtExpVMT", "outcome": "VMT", "status": "ok"}]},
            {"RPArtExpVMT": {"charts": {"Jobs and Dwelling": {"bad": "shape"}}}},
        )
        self.assertTrue(sections[0]["generic"])
        self.assertIn("specialized layout", sections[0]["fallback_reason"])

    def test_equity_has_specialized_cards(self):
        sections = render.build_sections(
            {"services": [{"service": "RPArtExpEquity", "outcome": "Equity", "status": "ok"}]},
            {"RPArtExpEquity": {"Population": 1000,
                                "Share of population living in EJ community": {
                                    "Within project location": 0.42,
                                    "Within community type": 0.25,
                                    "Within region": 0.2,
                                }}},
        )
        self.assertFalse(sections[0].get("generic", False))
        self.assertEqual(sections[0]["cards"][1]["rows"][0]["value_display"], "42.0%")

    def test_all_registered_services_render_into_one_offline_report(self):
        with tempfile.TemporaryDirectory() as run_dir:
            services = [
                {"service": service, "outcome": service, "status": "ok"}
                for service in dispatch.SERVICE_REGISTRY
            ]
            merged = {service: {} for service in dispatch.SERVICE_REGISTRY}
            merged["RPTitleAndGuide"] = {}
            manifest = {
                "timestamp": "20260812_120000_123456",
                "inputs": {
                    "program": "STIP", "report_name": "STIP",
                    "funding_program": "STIP", "project_name": "All Services",
                    "jurisdiction": "Sacramento", "project_type": "Non-Freeway Investment",
                    "aadt": 0, "pci": 0, "posted_speed": 0,
                },
                "services": services,
            }
            with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as stream:
                json.dump(manifest, stream)
            with open(os.path.join(run_dir, "merged.json"), "w", encoding="utf-8") as stream:
                json.dump(merged, stream)
            output = render.render_report(run_dir)
            with open(output, encoding="utf-8") as stream:
                html = stream.read()
            for service in dispatch.SERVICE_REGISTRY:
                if service != "RPTitleAndGuide":
                    self.assertIn(f'id="{service}"', html)
            self.assertIn("Report program", html)
            self.assertIn("View complete merged JSON output", html)


if __name__ == "__main__":
    unittest.main()
