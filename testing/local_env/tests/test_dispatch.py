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


class TestResolveDispatch(unittest.TestCase):
    def _services(self, program, ptype, outcomes=None):
        return [d["service"] for d in dispatch.resolve_dispatch(program, ptype, outcomes)]

    def test_cmcp_nonfreeway_all_matches_capture(self):
        # live_config_cmcp_run.json: title + 8, in this order
        got = self._services("CMCP US50", "Non-Freeway Investment")
        self.assertEqual(got, [
            "RPTitleAndGuide", "RPArtExpVMT", "RPArtExpCongestion", "RPArtExpMultiModal",
            "RPArtExpEconProsp", "RPArtExpFreight", "RPArtExpSafety", "RPArtSGRSGR", "RPArtExpEquity",
        ])

    def test_atp_nonfreeway_fixed_matches_capture(self):
        # live_config_atp_run.json: title + 5, in this order; Equity deliberately excluded
        got = self._services("Active Transportation Program", "Non-Freeway Investment")
        self.assertEqual(got, [
            "RPTitleAndGuide", "RPArtExpVMT", "RPArtExpSafety", "RPArtExpMultiModal",
            "RPArtExpEconProsp", "RPArtSGRSGR",
        ])

    def test_federal_matches_capture(self):
        nf = self._services("Regional Federal Funding Program", "Non-Freeway Investment")
        self.assertEqual(len(nf), 9)               # title + full 8
        self.assertIn("RPArtExpEquity", nf)
        fw = self._services("Regional Federal Funding Program", "Freeway Investment")
        self.assertEqual(len(fw), 7)               # title + full 6
        self.assertNotIn("RPArtSGRSGR", fw)

    def test_selectable_program_filters_by_selection(self):
        got = self._services("STIP", "Non-Freeway Investment",
                             ["Safety or Security", "Multimodal/Transportation Choice (Reduce VMT)"])
        # title always first; selected outcomes follow catalog order (VMT before Safety)
        self.assertEqual(got, ["RPTitleAndGuide", "RPArtExpVMT", "RPArtExpSafety"])

    def test_fixed_program_ignores_selection(self):
        got = self._services("Active Transportation Program", "Non-Freeway Investment",
                             ["Safety or Security"])  # selection ignored for fixed mode
        self.assertEqual(len(got), 6)

    def test_resolve_returns_full_registry_fields(self):
        first = dispatch.resolve_dispatch("STIP", "Non-Freeway Investment")[0]
        self.assertEqual(first["service"], "RPTitleAndGuide")
        self.assertEqual(first["folder"], "rp_title_guidepg")
        self.assertEqual(first["entry_function"], "make_title_guidepg_regpgm")


if __name__ == "__main__":
    unittest.main()
