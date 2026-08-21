import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config
import line_registry
import run_local


class TestPortableConfig(unittest.TestCase):
    def test_local_root_honors_environment(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, {"PPA3_LOCAL_ROOT": tmp}
        ):
            self.assertEqual(config.local_root(), config.Path(tmp).resolve())

    def test_explicit_python_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "python.exe")
            open(exe, "w").close()
            with mock.patch.dict(os.environ, {"PPA3_PRO_PYTHON": exe}):
                self.assertEqual(config.find_arcgis_python(), str(config.Path(exe).resolve()))

    def test_write_target_must_be_below_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = os.path.join(tmp, "child")
            self.assertEqual(config.assert_within_root(child, tmp), config.Path(child).resolve())
            with self.assertRaises(ValueError):
                config.assert_within_root(tmp, tmp)

    def test_candidate_runtime_path_is_inside_selected_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            line = line_registry.load(tmp)["TestTruxelBridge"]
            self.assertEqual(
                line["fc_path"], os.path.join(tmp, "PPA3Testing.gdb", "TestTruxelBridge")
            )
            self.assertTrue(line["source_path"].startswith("I:"))

    def test_service_scratch_is_private_and_beside_run_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = os.path.join(tmp, "_sample.json")
            first = run_local.create_private_scratch(sample, "RPTitleAndGuide")
            second = run_local.create_private_scratch(sample, "RPTitleAndGuide")
            self.assertNotEqual(first, second)
            self.assertEqual(os.path.dirname(first), tmp)
            self.assertEqual(os.path.dirname(second), tmp)


if __name__ == "__main__":
    unittest.main()
