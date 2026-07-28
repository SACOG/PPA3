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
            "project_line": "TestTruxelBridge",
            "project_name": "t", "jurisdiction": "Sacramento",
            "aadt": "0", "posted_speed": "0", "pci": "0", "email": "x@y.com",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("20260101_000000", resp.headers["Location"])
        self.assertEqual(captured["program"], "Active Transportation Program")
        self.assertEqual(captured["project_line"],
                         r"I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge")


if __name__ == "__main__":
    unittest.main()
