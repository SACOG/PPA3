import os
import sys
import unittest

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
            "funding_program": "Active Transportation",
            "project_line": "TestTruxelBridge",
            "project_name": "t", "jurisdiction": "Sacramento",
            "aadt": "0", "posted_speed": "0", "pci": "0", "email": "x@y.com",
            "confirm_email": "x@y.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("20260101_000000", resp.headers["Location"])
        self.assertEqual(captured["program"], "Active Transportation Program")
        self.assertEqual(captured["funding_program"], "Active Transportation")
        self.assertEqual(captured["project_line"],
                         r"C:\PPA3Testing\PPA3Testing.gdb\TestTruxelBridge")

    def test_form_exposes_live_contract_fields(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Confirm Email", html)
        self.assertIn("Funding program", html)
        self.assertIn("Developer override", html)
        self.assertIn("Dispatch preview", html)
        self.assertIn("System Preservation Program", html)

    def test_current_atp_preview_includes_equity(self):
        response = self.client.post("/api/dispatch-preview", json={
            "program": "Active Transportation Program",
            "project_type": "Non-Freeway Investment",
            "selected_outcomes": [],
            "developer_override": False,
        })
        services = [item["service"] for item in response.get_json()["services"]]
        self.assertEqual(len(services), 7)
        self.assertIn("RPArtExpEquity", services)

    def test_selectable_none_preview_runs_title_only(self):
        response = self.client.post("/api/dispatch-preview", json={
            "program": "STIP", "project_type": "Non-Freeway Investment",
            "selected_outcomes": [], "developer_override": False,
        })
        self.assertEqual(
            [item["service"] for item in response.get_json()["services"]],
            ["RPTitleAndGuide"],
        )

    def test_mismatched_email_is_rejected_before_run(self):
        response = self.client.post("/run", data={
            "program": "STIP", "project_type": "Non-Freeway Investment",
            "project_line": "TestTruxelBridge", "project_name": "Test One",
            "jurisdiction": "Sacramento", "aadt": "0", "posted_speed": "0", "pci": "0",
            "email": "x@y.com", "confirm_email": "other@y.com",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("must match", response.get_data(as_text=True))


import json, tempfile

class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.tmp = tempfile.mkdtemp()
        webapp.app.config["RUNS_ROOT"] = self.tmp
        run_dir = os.path.join(self.tmp, "20260101_000000")
        os.makedirs(run_dir)
        json.dump({"timestamp": "20260101_000000",
                   "inputs": {"program": "STIP", "project_type": "Non-Freeway Investment"},
                   "services": [{"service": "RPTitleAndGuide", "outcome": "(title)", "status": "ok"},
                                {"service": "RPArtExpSafety", "outcome": "Safety or Security",
                                 "status": "failed"}]},
                  open(os.path.join(run_dir, "manifest.json"), "w"))
        json.dump({"total": 6}, open(os.path.join(run_dir, "RPTitleAndGuide.json"), "w"))
        with open(os.path.join(run_dir, "RPArtExpSafety.log"), "w") as stream:
            stream.write("synthetic failure")

    def test_detail_shows_services_and_statuses(self):
        html = self.client.get("/run/20260101_000000").get_data(as_text=True)
        self.assertIn("RPArtExpSafety", html)
        self.assertIn("failed", html)
        self.assertIn("Safety or Security", html)

    def test_history_lists_the_run(self):
        html = self.client.get("/runs").get_data(as_text=True)
        self.assertIn("20260101_000000", html)

    def test_registered_log_artifact_is_available(self):
        response = self.client.get("/run/20260101_000000/artifact/RPArtExpSafety.log")
        self.assertEqual(response.status_code, 200)
        self.assertIn("synthetic failure", response.get_data(as_text=True))

    def test_artifact_route_rejects_unregistered_paths(self):
        response = self.client.get("/run/20260101_000000/artifact/_sample.json")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
