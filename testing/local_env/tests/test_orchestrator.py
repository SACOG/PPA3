import os
import sys
import json
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
import orchestrator


class TestRunReport(unittest.TestCase):
    def _inputs(self):
        return dict(
            program="Active Transportation Program", project_type="Non-Freeway Investment",
            selected_outcomes=None, project_line=r"C:\fake\line", project_name="t",
            jurisdiction="Sacramento", aadt=0, posted_speed=0, pci=0, email="x@y.com",
        )

    def _fake_runner(self, service, sample_path, out_dir):
        # emulate a successful service run: write a tiny result json
        p = os.path.join(out_dir, service + ".json")
        with open(p, "w") as f:
            json.dump({"service": service, "ok": True}, f)
        return ("ok", p, f"ran {service}\n")

    def test_creates_run_folder_with_manifest_and_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(self._inputs(), runs_root=tmp, _runner=self._fake_runner)
            self.assertTrue(os.path.isdir(run_dir))
            manifest = json.load(open(os.path.join(run_dir, "manifest.json")))
            # ATP non-freeway dispatches title + 5 = 6 services
            self.assertEqual(len(manifest["services"]), 6)
            self.assertTrue(all(s["status"] == "ok" for s in manifest["services"]))
            merged = json.load(open(os.path.join(run_dir, "merged.json")))
            self.assertEqual(len(merged), 6)
            self.assertIn("RPArtExpSafety", merged)

    def test_failing_service_recorded_and_run_continues(self):
        def flaky(service, sample_path, out_dir):
            if service == "RPArtExpSafety":
                return ("failed", None, "boom\n")
            return self._fake_runner(service, sample_path, out_dir)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(self._inputs(), runs_root=tmp, _runner=flaky)
            manifest = json.load(open(os.path.join(run_dir, "manifest.json")))
            statuses = {s["service"]: s["status"] for s in manifest["services"]}
            self.assertEqual(statuses["RPArtExpSafety"], "failed")
            self.assertEqual(statuses["RPArtExpVMT"], "ok")  # others still ran


if __name__ == "__main__":
    unittest.main()
