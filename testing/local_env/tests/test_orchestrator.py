import os
import sys
import json
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
import orchestrator


def _read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


class TestRunReport(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.config_patch = mock.patch.object(orchestrator.config, "local_root")
        mocked_root = self.config_patch.start()
        mocked_root.return_value = orchestrator.config.Path(self.sandbox.name)
        os.makedirs(os.path.join(self.sandbox.name, "globalconfig"))
        with open(os.path.join(self.sandbox.name, "globalconfig", "parameters.py"), "w") as stream:
            stream.write("# synthetic local config\n")
        with open(os.path.join(self.sandbox.name, "globalconfig", "data_paths.yaml"), "w") as stream:
            stream.write("server_data:\n  gisdir:\n    archived_run_db: PPA3Testing_run.gdb\n")
        os.makedirs(os.path.join(self.sandbox.name, "PPA3Testing_run.gdb"))

    def tearDown(self):
        self.config_patch.stop()
        self.sandbox.cleanup()

    def _inputs(self):
        return dict(
            program="Active Transportation Program", project_type="Non-Freeway Investment",
            selected_outcomes=None, project_line=r"C:\fake\line", project_name="t",
            report_name="Active Transportation Program", funding_program="Active Transportation",
            developer_override=False, jurisdiction="Sacramento", aadt=0, posted_speed=0, pci=0,
            email="x@y.com",
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
            manifest = _read_json(os.path.join(run_dir, "manifest.json"))
            # Current ATP non-freeway workflow dispatches title + 6 = 7 services.
            self.assertEqual(len(manifest["services"]), 7)
            self.assertTrue(all(s["status"] == "ok" for s in manifest["services"]))
            merged = _read_json(os.path.join(run_dir, "merged.json"))
            self.assertEqual(len(merged), 7)
            self.assertIn("RPArtExpSafety", merged)
            self.assertEqual(manifest["report_status"], "ok")
            self.assertTrue(os.path.isfile(os.path.join(run_dir, "report.html")))
            sample = _read_json(os.path.join(run_dir, "_sample.json"))
            self.assertEqual(sample["Funding_Program"], "Active Transportation")

    def test_failing_service_recorded_and_run_continues(self):
        def flaky(service, sample_path, out_dir):
            if service == "RPArtExpSafety":
                return ("failed", None, "boom\n")
            return self._fake_runner(service, sample_path, out_dir)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(self._inputs(), runs_root=tmp, _runner=flaky)
            manifest = _read_json(os.path.join(run_dir, "manifest.json"))
            statuses = {s["service"]: s["status"] for s in manifest["services"]}
            self.assertEqual(statuses["RPArtExpSafety"], "failed")
            self.assertEqual(statuses["RPArtExpVMT"], "ok")  # ran before the failure
            self.assertEqual(statuses["RPArtSGRSGR"], "ok")  # last service, ran after the failure

    def test_runner_exception_is_recorded_and_run_continues(self):
        def exploding(service, sample_path, out_dir):
            if service == "RPArtExpSafety":
                raise RuntimeError("simulated runner crash")
            return self._fake_runner(service, sample_path, out_dir)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(self._inputs(), runs_root=tmp, _runner=exploding)
            manifest = _read_json(os.path.join(run_dir, "manifest.json"))
            safety = next(s for s in manifest["services"] if s["service"] == "RPArtExpSafety")
            self.assertEqual(safety["status"], "failed")
            self.assertIn("simulated runner crash", safety["error"])
            self.assertEqual(manifest["status"], "complete_with_errors")
            self.assertEqual(manifest["services"][-1]["status"], "ok")

    def test_manifest_records_override_and_distinct_funding_program(self):
        inputs = self._inputs()
        inputs.update({
            "program": "Regional Federal Funding Program",
            "report_name": "Regional Federal Funding Program",
            "funding_program": "System Preservation Program",
            "developer_override": True,
            "selected_outcomes": ["Safety or Security"],
        })
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = orchestrator.run_report(inputs, runs_root=tmp, _runner=self._fake_runner)
            manifest = _read_json(os.path.join(run_dir, "manifest.json"))
            self.assertTrue(manifest["inputs"]["developer_override"])
            self.assertEqual(manifest["inputs"]["funding_program"], "System Preservation Program")
            self.assertEqual(len(manifest["services"]), 2)

    def test_parent_cleanup_removes_only_matching_private_scratch(self):
        with tempfile.TemporaryDirectory() as run_dir:
            matching = os.path.join(run_dir, "scratch_RPTitleAndGuide_abc")
            other = os.path.join(run_dir, "scratch_OtherService_xyz")
            os.makedirs(matching)
            os.makedirs(other)
            orchestrator._cleanup_private_scratch(run_dir, "RPTitleAndGuide")
            self.assertFalse(os.path.exists(matching))
            self.assertTrue(os.path.isdir(other))


if __name__ == "__main__":
    unittest.main()
