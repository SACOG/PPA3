import ast
import os
import unittest


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class TestCallableEntrypointBindings(unittest.TestCase):
    CASES = {
        "rp_artexp_vmt/run_vmt_report.py": ("make_vmt_report_artexp", {"project_name", "output_dir"}),
        "rp_artexp_saf/run_artexp_safety_report.py": ("make_safety_report_artexp", {"project_fc", "output_dir"}),
        "rp_artexp_econ/run_econprosp_report.py": ("make_econ_report_artexp", {"project_fc", "output_dir"}),
        "rp_artexp_eq/run_equity_report.py": ("make_equity_rpt_artexp", {"project_fc", "output_dir"}),
        "rp_artsgr_sgr/run_artsgr_sgr_report.py": ("make_sgr_report_artsgr", {"output_dir"}),
        "rp_artexp_cong/run_congestion_report.py": (
            "make_congestion_rpt_artexp",
            {"project_fc", "project_type", "project_name", "aadt", "output_dir"},
        ),
        "rp_artexp_frgt/run_artexp_freight_report.py": (
            "make_frgt_report_artexp", {"project_type", "output_dir"},
        ),
        "rp_fwyexp_vmt/run_vmt_report.py": ("make_vmt_report_fwyexp", {"output_dir"}),
        "rp_fwyexp_cong/run_congestion_report.py": (
            "make_congestion_rpt_fwyexp", {"project_fc", "output_dir"},
        ),
        "rp_fwyexp_mm/run_mm_report.py": ("make_mm_report_fwyexp", {"output_dir"}),
        "rp_fwyexp_econ/run_econprosp_report.py": ("make_econ_report_fwyexp", {"output_dir"}),
        "rp_fwyexp_frgt/run_fwy_freight_report.py": (
            "make_freight_rept_fwyexp", {"output_dir"},
        ),
        "rp_fwyexp_saf/run_fwyexp_safety_report.py": (
            "make_safety_report_fwyexp", {"project_fc", "output_dir"},
        ),
    }

    def test_function_only_runtime_names_are_bound_inside_entrypoint(self):
        base = os.path.join(REPO, "gp-services", "regionalprogram")
        for relative, (function_name, expected) in self.CASES.items():
            with self.subTest(service=relative):
                with open(os.path.join(base, relative), encoding="utf-8") as stream:
                    tree = ast.parse(stream.read())
                function = next(
                    node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == function_name
                )
                bound = {
                    node.id for node in ast.walk(function)
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                }
                self.assertTrue(expected <= bound, f"unbound callable runtime names: {expected - bound}")


if __name__ == "__main__":
    unittest.main()
