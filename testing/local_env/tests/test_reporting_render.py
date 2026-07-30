import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
from reporting import cards, render


class TestRenderHtmlSkeleton(unittest.TestCase):
    def test_renders_section_titles_and_chart_canvas(self):
        layout = {
            "service": "RPArtSGRSGR",
            "section_title": "Maintain State of Good Repair",
            "cards": [
                {"type": "kpi", "source": "ADT", "subtitle": "Average Daily Traffic (ADT)"},
                {
                    "type": "chart",
                    "source_chart": "Jobs and Dwelling",
                    "x_field": "year",
                    "series": [{"field": "jobs", "label": "Jobs"}],
                },
            ],
        }
        data = {"ADT": 15000, "charts": {"Jobs and Dwelling": {"features": [
            {"attributes": {"year": "2020", "jobs": 100}},
        ]}}}
        section = cards.build_section(layout, data)
        html = render.render_html([section], project_title="Test Project")

        self.assertIn("Test Project", html)
        self.assertIn("Maintain State of Good Repair", html)
        self.assertIn("Average Daily Traffic (ADT)", html)
        self.assertIn("15,000", html)
        self.assertIn('class="chart-canvas"', html)
        self.assertIn("chart.umd.min.js", html)

    def test_unavailable_section_renders_placeholder(self):
        section = {"service": "RPArtExpEquity", "section_title": "Equity", "unavailable": True, "cards": []}
        html = render.render_html([section], project_title="Test Project")
        self.assertIn("section-unavailable", html)


class TestBuildProjectContext(unittest.TestCase):
    def test_pulls_from_manifest_inputs_and_title_service(self):
        manifest = {
            "timestamp": "20260729_172109",
            "inputs": {
                "program": "Active Transportation Program",
                "project_type": "Non-Freeway Investment",
                "project_name": "verify_run",
                "jurisdiction": "Sacramento",
                "aadt": 15000,
                "posted_speed": 35,
                "pci": 70,
            },
        }
        merged = {"RPTitleAndGuide": {
            "Project Length Centerline Miles": 0.6674009841521,
            "Project Community Type": "Established Communities",
            "Project Unique ID": "fb86f0b5-9b1d-4774-bbcd-889ec7306d69",
        }}
        ctx = render.build_project_context(manifest, merged, report_generated="Wednesday, July 29, 2026")
        self.assertEqual(ctx["name"], "verify_run")
        self.assertEqual(ctx["jurisdiction"], "Sacramento")
        self.assertEqual(ctx["funding_program"], "Active Transportation Program")
        self.assertEqual(ctx["length_miles"], 0.67)
        self.assertEqual(ctx["community_type"], "Established Communities")
        self.assertEqual(ctx["uid"], "fb86f0b5-9b1d-4774-bbcd-889ec7306d69")
        self.assertEqual(ctx["report_generated"], "Wednesday, July 29, 2026")


class TestBuildSections(unittest.TestCase):
    def test_skips_title_includes_ok_services_flags_missing(self):
        manifest = {"services": [
            {"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
            {"service": "RPArtSGRSGR", "outcome": "Maintain State of Good Repair", "status": "ok"},
            {"service": "RPArtExpVMT", "outcome": "Multimodal/Transportation Choice (Reduce VMT)", "status": "failed(x)"},
        ]}
        merged = {"RPArtSGRSGR": {"Pavement Condition Index": 70, "ADT": 15000, "Complete Streets Index": 3.8}}
        sections = render.build_sections(manifest, merged)
        # RPArtSGRSGR has a real layout config (authored in Task 9) -> should render normally
        sgr = next(s for s in sections if s["service"] == "RPArtSGRSGR")
        self.assertFalse(sgr["unavailable"])
        # RPArtExpVMT failed upstream -> unavailable, no crash
        vmt = next(s for s in sections if s["service"] == "RPArtExpVMT")
        self.assertTrue(vmt["unavailable"])
        # Title is never treated as an outcome section
        self.assertNotIn("RPTitleAndGuide", [s["service"] for s in sections])


class TestRenderReport(unittest.TestCase):
    def test_writes_report_html_from_a_run_dir(self):
        with tempfile.TemporaryDirectory() as run_dir:
            manifest = {
                "timestamp": "20260729_172109",
                "inputs": {
                    "program": "Active Transportation Program", "project_type": "Non-Freeway Investment",
                    "project_name": "verify_run", "jurisdiction": "Sacramento",
                    "aadt": 15000, "posted_speed": 35, "pci": 70,
                },
                "services": [
                    {"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
                    {"service": "RPArtSGRSGR", "outcome": "Maintain State of Good Repair", "status": "ok"},
                ],
            }
            merged = {
                "RPTitleAndGuide": {
                    "Project Length Centerline Miles": 0.6674, "Project Community Type": "Established Communities",
                    "Project Unique ID": "abc-123",
                },
                "RPArtSGRSGR": {"Pavement Condition Index": 70, "ADT": 15000, "Complete Streets Index": 3.8},
            }
            with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            with open(os.path.join(run_dir, "merged.json"), "w", encoding="utf-8") as f:
                json.dump(merged, f)

            out_path = render.render_report(run_dir)

            self.assertTrue(os.path.isfile(out_path))
            with open(out_path, encoding="utf-8") as f:
                html = f.read()
            self.assertIn("verify_run", html)
            self.assertIn("Maintain State of Good Repair", html)
            self.assertIn("Using This Report", html)
            self.assertIn("Active Transportation Program", html)  # ATP intro included

            # Fix 1 regression check: assets must be inlined, not relative-linked.
            # Prevents accidental revert of inline CSS/JS fix (report.html renders blank if
            # it tries to load static/report.css and static/chart.umd.min.js as relative paths
            # from an arbitrary run_dir -- those files never exist there).
            self.assertNotIn('href="static/', html, "CSS must be inlined, not linked as static/report.css")
            self.assertNotIn('src="static/', html, "JS must be inlined, not linked as static/chart.umd.min.js")
            # A distinctive CSS rule from report.css must be inlined, not linked.
            self.assertIn(".report-title", html, "report.css styles must be inlined")
            # A distinctive string from the vendored Chart.js build must be inlined, not linked.
            self.assertIn("Chart.js", html, "Chart.js must be inlined")


LOCAL_ATP_RUN_DIR = os.path.join(os.path.dirname(HERE), "out", "runs", "20260729_172109")


@unittest.skipUnless(os.path.isdir(LOCAL_ATP_RUN_DIR), "local ATP harness run not present")
class TestRenderRealLocalRun(unittest.TestCase):
    def test_renders_all_five_atp_sections_with_no_placeholders(self):
        out_path = render.render_report(
            LOCAL_ATP_RUN_DIR,
            output_path=os.path.join(tempfile.mkdtemp(), "report.html"),
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()

        # All 5 ATP outcome section headers present
        for title in [
            "Multimodal/Transportation Choice (Reduce VMT)",
            "Safety",
            "Multimodal/Transportation Choice (Encourage Multimodal Travel)",
            "Economic Prosperity",
            "Maintain State of Good Repair",
        ]:
            self.assertIn(title, html, f"missing section: {title}")

        # No section fell back to "unavailable" and no card silently reported "(no data)".
        # NOTE: checking for the bare substring "section-unavailable" would false-positive now
        # that report.css is inlined (Fix 1) -- the CSS rule `.section-unavailable { ... }`
        # itself contains that substring. Check for the actual rendered usage instead (the
        # class attribute section.html.j2 emits on the placeholder <p>, see cards.py/render.py
        # "unavailable" section fallback shape).
        self.assertNotIn('class="section-unavailable"', html)
        self.assertNotIn("(no data)", html)

        # Title-page fields sourced from this specific run's manifest.json
        self.assertIn("verify_run", html)
        self.assertIn("Sacramento", html)

    def test_report_is_fully_offline_no_relative_static_paths(self):
        # Fix 1 regression: report.html.j2 used to link static/report.css and
        # static/chart.umd.min.js as paths RELATIVE TO THE OUTPUT FILE, but that static/ dir
        # never exists next to a rendered report.html in a run_dir -- every chart rendered as
        # a blank canvas and the report was entirely unstyled. Both assets must now be inlined.
        out_path = render.render_report(
            LOCAL_ATP_RUN_DIR,
            output_path=os.path.join(tempfile.mkdtemp(), "report.html"),
        )
        with open(out_path, encoding="utf-8") as f:
            html = f.read()

        self.assertNotIn('href="static/', html)
        self.assertNotIn('src="static/', html)
        # A distinctive CSS rule from report.css must be inlined, not linked.
        self.assertIn(".report-title", html)
        # A distinctive string from the vendored Chart.js build must be inlined, not linked.
        self.assertIn("Chart.js", html)


class TestBuildSectionsExceptionSafety(unittest.TestCase):
    """Fix 2 regression: build_sections() must degrade a single malformed service to an
    "unavailable" section instead of letting cards.py's builders crash the whole render."""

    def test_ok_service_with_none_data_degrades_to_unavailable(self):
        manifest = {"services": [
            {"service": "RPArtSGRSGR", "outcome": "Maintain State of Good Repair", "status": "ok"},
        ]}
        merged = {"RPArtSGRSGR": None}
        sections = render.build_sections(manifest, merged)
        self.assertEqual(len(sections), 1)
        self.assertTrue(sections[0]["unavailable"])
        self.assertEqual(sections[0]["cards"], [])

    def test_chart_card_missing_features_key_degrades_to_unavailable(self):
        manifest = {"services": [
            {"service": "RPArtExpVMT", "outcome": "Multimodal/Transportation Choice (Reduce VMT)", "status": "ok"},
        ]}
        # "charts" present but the named chart dict has no "features" key -> cards.build_chart_card
        # would raise KeyError on raw["features"] without the try/except guard. "Jobs and
        # Dwelling" is the actual source_chart key the RPArtExpVMT layout's first card reads
        # (its subtitle "Jobs and Houses nearby by 2035" is a different, display-only string).
        merged = {"RPArtExpVMT": {"charts": {"Jobs and Dwelling": {"title": "t"}}}}
        sections = render.build_sections(manifest, merged)
        self.assertEqual(len(sections), 1)
        self.assertTrue(sections[0]["unavailable"])

    def test_manifest_entry_missing_service_key_is_skipped_not_raised(self):
        manifest = {"services": [
            {"outcome": "no service key here", "status": "ok"},
            {"service": "RPArtSGRSGR", "outcome": "Maintain State of Good Repair", "status": "failed(x)"},
        ]}
        merged = {}
        sections = render.build_sections(manifest, merged)
        # The malformed entry is skipped entirely; only the valid one produces a section.
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["service"], "RPArtSGRSGR")


class TestFormatStampFallback(unittest.TestCase):
    """Fix 2 regression: _format_stamp() must not crash render_report() over a missing or
    malformed manifest["timestamp"] -- that's a title-page cosmetic field, not worth a hard
    failure."""

    def test_missing_timestamp_falls_back(self):
        self.assertEqual(render._format_stamp(None), "(unknown)")

    def test_malformed_timestamp_falls_back(self):
        self.assertEqual(render._format_stamp("not-a-timestamp"), "(unknown)")

    def test_render_report_survives_missing_timestamp_in_manifest(self):
        with tempfile.TemporaryDirectory() as run_dir:
            manifest = {
                "inputs": {"program": "Active Transportation Program", "project_name": "no_timestamp_run"},
                "services": [],
            }
            merged = {}
            with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            with open(os.path.join(run_dir, "merged.json"), "w", encoding="utf-8") as f:
                json.dump(merged, f)

            out_path = render.render_report(run_dir)
            with open(out_path, encoding="utf-8") as f:
                html = f.read()
            self.assertIn("(unknown)", html)


if __name__ == "__main__":
    unittest.main()
