import os
import shutil
import sys
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "webapp"))
sys.path.insert(0, os.path.dirname(HERE))
import app as webapp


class TestForm(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_form_lists_all_four_programs(self):
        html = self.client.get("/").get_data(as_text=True)
        for prog in ["STIP", "CMCP US50", "Active Transportation Program",
                     "Regional Federal Funding Program"]:
            self.assertIn(prog, html)

    def test_form_lists_sample_lines(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("TestTruxelBridge", html)

    def test_post_run_invokes_orchestrator_and_redirects(self):
        captured = {}
        def fake_run_report(inputs):
            captured.update(inputs)
            return r"C:\fake\out\runs\20260101_000000"
        webapp.app.config["RUN_REPORT"] = fake_run_report
        resp = self.client.post("/run", data={
            "program": "Active Transportation Program",
            "project_type": "Non-Freeway Investment",
            "project_line": "TestTruxelBridge",
            "project_name": "t", "jurisdiction": "Sacramento",
            "aadt": "0", "posted_speed": "0", "pci": "0", "email": "x@y.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("20260101_000000", resp.headers["Location"])
        self.assertEqual(captured["program"], "Active Transportation Program")
        self.assertEqual(captured["project_line"],
                         r"I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge")


import json, tempfile

class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.tmp = tempfile.mkdtemp()
        webapp.app.config["RUNS_ROOT"] = self.tmp
        run_dir = os.path.join(self.tmp, "20260101_000000")
        os.makedirs(run_dir)
        json.dump({"timestamp": "20260101_000000",
                   "inputs": {"program": "STIP", "project_type": "Non-Freeway Investment",
                              "project_name": "TruxelBridgeFixture", "jurisdiction": "Sacramento",
                              "aadt": 0, "posted_speed": 0, "pci": 0},
                   "services": [{"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
                                {"service": "RPArtExpSafety", "outcome": "Safety or Security",
                                 "status": "failed"}]},
                  open(os.path.join(run_dir, "manifest.json"), "w"))
        json.dump({"total": 6}, open(os.path.join(run_dir, "RPTitleAndGuide.json"), "w"))
        json.dump({"RPTitleAndGuide": {
                       "Project Length Centerline Miles": 0.5,
                       "Project Community Type": "Established Communities",
                       "Project Unique ID": "test-uid-123",
                   }},
                  open(os.path.join(run_dir, "merged.json"), "w"))

    def test_detail_shows_services_and_statuses(self):
        html = self.client.get("/run/20260101_000000").get_data(as_text=True)
        self.assertIn("RPArtExpSafety", html)
        self.assertIn("failed", html)
        self.assertIn("Safety or Security", html)

    def test_history_lists_the_run(self):
        html = self.client.get("/runs").get_data(as_text=True)
        self.assertIn("20260101_000000", html)

    def test_report_route_renders_html_for_a_valid_run(self):
        resp = self.client.get("/run/20260101_000000/report")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Using This Report", html)
        self.assertIn("TruxelBridgeFixture", html)  # project_name from the fixture's inputs

    def test_report_route_404s_for_unknown_stamp(self):
        resp = self.client.get("/run/nonexistent-stamp/report")
        self.assertEqual(resp.status_code, 404)

    def test_detail_page_links_to_report(self):
        html = self.client.get("/run/20260101_000000").get_data(as_text=True)
        self.assertIn('href="/run/20260101_000000/report"', html)

    def _make_escape_target(self, name):
        """A directory OUTSIDE self.tmp (RUNS_ROOT) that is a fully valid "run" -- i.e. it has
        both manifest.json and merged.json, so render_report() would actually succeed and write
        report.html into it if a traversal stamp reached it. Without this, a traversal test would
        be vacuous: the pre-existing manifest.json-exists check would 404 it for an unrelated
        reason before the stamp guard is ever exercised (this is exactly what happened when this
        test was first written pointing at a nonexistent "outside" dir -- it passed even against
        the unfixed, vulnerable code).

        `name` is suffixed with a fresh uuid so re-runs never collide with a leftover directory
        from a previous interrupted run in the shared OS temp root (self.tmp's parent).
        """
        outside_dir = os.path.join(os.path.dirname(self.tmp), f"{name}_{uuid.uuid4().hex}")
        os.makedirs(outside_dir, exist_ok=True)
        self.addCleanup(shutil.rmtree, outside_dir, True)
        json.dump({"timestamp": "20260101_000000",
                   "inputs": {"program": "STIP", "project_type": "Non-Freeway Investment",
                              "project_name": "ShouldNeverRender", "jurisdiction": "Sacramento",
                              "aadt": 0, "posted_speed": 0, "pci": 0},
                   "services": []},
                  open(os.path.join(outside_dir, "manifest.json"), "w"))
        json.dump({}, open(os.path.join(outside_dir, "merged.json"), "w"))
        return outside_dir

    def test_report_route_404s_for_path_traversal_stamp_and_writes_nothing_outside_runs_root(self):
        outside_dir = self._make_escape_target("webapp_traversal_target_1")
        target_name = os.path.basename(outside_dir)
        before = set(os.listdir(outside_dir))
        resp = self.client.get(f"/run/..%5C{target_name}/report")
        self.assertEqual(resp.status_code, 404)
        after = set(os.listdir(outside_dir))
        self.assertEqual(before, after,
                          "traversal request must not write report.html outside RUNS_ROOT")
        self.assertFalse(os.path.exists(os.path.join(outside_dir, "report.html")))

    def test_report_route_404s_for_literal_backslash_traversal_stamp(self):
        outside_dir = self._make_escape_target("webapp_traversal_target_2")
        target_name = os.path.basename(outside_dir)
        resp = self.client.get("/run/" + f"..\\{target_name}" + "/report")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(os.path.exists(os.path.join(outside_dir, "report.html")))

    def test_detail_route_404s_for_path_traversal_stamp(self):
        outside_dir = self._make_escape_target("webapp_traversal_target_3")
        target_name = os.path.basename(outside_dir)
        resp = self.client.get(f"/run/..%5C{target_name}")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
