import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # testing/local_env
import dispatch


class TestServiceMaps(unittest.TestCase):
    def test_registry_has_all_15_live_services(self):
        expected = {
            "RPTitleAndGuide", "RPArtExpVMT", "RPArtExpCongestion", "RPArtExpMultiModal",
            "RPArtExpEconProsp", "RPArtExpFreight", "RPArtExpSafety", "RPArtSGRSGR",
            "RPArtExpEquity", "RPFwyExpVMT", "RPFwyExpCongestion", "RPFwyExpMultiModal",
            "RPFwyExpEconProsp", "RPFwyExpFreight", "RPFwyExpSafety",
        }
        self.assertEqual(set(dispatch.SERVICE_REGISTRY), expected)

    def test_registry_entries_point_at_real_files(self):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        for svc, (folder, module, fn) in dispatch.SERVICE_REGISTRY.items():
            path = os.path.join(repo, "gp-services", "regionalprogram", folder, module + ".py")
            self.assertTrue(os.path.isfile(path), f"{svc}: missing {path}")

    def test_nonfreeway_map_matches_capture(self):
        m = dispatch.OUTCOME_SERVICE_MAP["Non-Freeway Investment"]
        self.assertEqual(m["Safety or Security"], "RPArtExpSafety")
        self.assertEqual(m["Maintain State of Good Repair"], "RPArtSGRSGR")
        self.assertEqual(m["Benefits to the Transportation Network and Impacted Communities"],
                         "RPArtExpEquity")

    def test_freeway_map_matches_capture(self):
        m = dispatch.OUTCOME_SERVICE_MAP["Freeway Investment"]
        self.assertEqual(m["Safety or Security"], "RPFwyExpSafety")
        self.assertNotIn("Maintain State of Good Repair", m)  # freeway has no SGR


if __name__ == "__main__":
    unittest.main()
