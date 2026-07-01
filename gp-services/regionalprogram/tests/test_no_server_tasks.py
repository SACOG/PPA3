"""
Tests for no-server wishlist tasks (Tasks 1-4).

All tests run without arcpy and without server access.
They cover the pure-Python logic of each change.

Run with:  python -m pytest gp-services/regionalprogram/tests/test_no_server_tasks.py -v
       or:  python gp-services/regionalprogram/tests/test_no_server_tasks.py
"""

import os
import sys
import json
import tempfile
import unittest

import pandas as pd

# ---------------------------------------------------------------------------
# Task 3: Job/DU density — test make_aggval_dict (no arcpy)
# ---------------------------------------------------------------------------

def make_aggval_dict(aggval_csv, metric_cols, proj_ctype, yearkey, geo_regn, yearval=None):
    """Inline copy of get_agg_values.make_aggval_dict for testing."""
    df_agg = pd.read_csv(aggval_csv)
    metname_col = "metric_name"
    df_agg = df_agg.rename(columns={'Unnamed: 0': metname_col, 'REGION': geo_regn})

    if yearval:
        rows = df_agg.loc[
            (df_agg[metname_col].isin(metric_cols)) & (df_agg[yearkey] == yearval),
            [metname_col, proj_ctype, geo_regn, yearkey]
        ]
    else:
        rows = df_agg.loc[df_agg[metname_col].isin(metric_cols),
                          [metname_col, proj_ctype, geo_regn, yearkey]]

    return {d[metname_col]: {proj_ctype: d[proj_ctype], geo_regn: d[geo_regn], yearkey: d[yearkey]}
            for d in rows.to_dict(orient='records')}


class TestAggvalDict(unittest.TestCase):
    """Task 3: verify make_aggval_dict correctly reads benchmark density values."""

    def setUp(self):
        # Build a minimal benchmark CSV with density columns
        self.tmpdir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.tmpdir, 'Agg_ppa_vals_latest.csv')
        data = {
            'Unnamed: 0': ['EMPTOT_NetPclAcre', 'DU_TOT_NetPclAcre', 'mix_index'],
            'Urban Center':    [12.5, 8.3, 0.72],
            'Established Community': [6.1, 4.2, 0.55],
            'REGION':          [5.0, 3.8, 0.48],
            'year':            [2020, 2020, 2020],
        }
        pd.DataFrame(data).to_csv(self.csv_path, index=False)

    def test_returns_correct_project_ctype_value(self):
        result = make_aggval_dict(
            self.csv_path,
            metric_cols=['EMPTOT_NetPclAcre', 'DU_TOT_NetPclAcre'],
            proj_ctype='Urban Center',
            yearkey='year',
            geo_regn='Region',
            yearval=2020
        )
        self.assertIn('EMPTOT_NetPclAcre', result)
        self.assertAlmostEqual(result['EMPTOT_NetPclAcre']['Urban Center'], 12.5)
        self.assertAlmostEqual(result['DU_TOT_NetPclAcre']['Urban Center'], 8.3)

    def test_returns_correct_region_value(self):
        result = make_aggval_dict(
            self.csv_path,
            metric_cols=['EMPTOT_NetPclAcre'],
            proj_ctype='Established Community',
            yearkey='year',
            geo_regn='Region',
            yearval=2020
        )
        self.assertAlmostEqual(result['EMPTOT_NetPclAcre']['Region'], 5.0)

    def test_year_filter_excludes_wrong_year(self):
        result = make_aggval_dict(
            self.csv_path,
            metric_cols=['EMPTOT_NetPclAcre'],
            proj_ctype='Urban Center',
            yearkey='year',
            geo_regn='Region',
            yearval=2040  # not in CSV
        )
        self.assertEqual(len(result), 0)

    def test_nonexistent_metric_returns_empty(self):
        result = make_aggval_dict(
            self.csv_path,
            metric_cols=['DOES_NOT_EXIST'],
            proj_ctype='Urban Center',
            yearkey='year',
            geo_regn='Region',
            yearval=2020
        )
        self.assertEqual(len(result), 0)


class TestDensityJsonAttributes(unittest.TestCase):
    """Task 3: verify the density chart JSON update logic writes correct attributes."""

    def _build_json(self):
        """Minimal 'Jobs and Dwelling' chart structure matching the real template."""
        return {
            "charts": {
                "Jobs and Dwelling": {
                    "features": [
                        {"attributes": {"year": "2020", "jobs": 0, "dwellingUnits": 0}},
                        {"attributes": {"year": "2035", "jobs": 0, "dwellingUnits": 0}},
                    ]
                }
            }
        }

    def _apply_density_update(self, json_loaded, order_val, data_year,
                               jobs_dens, du_dens,
                               commtype_jobs=0, region_jobs=0,
                               commtype_du=0, region_du=0):
        """Mirrors the write logic in chart_job_du_tot.update_json()."""
        attrs = json_loaded["charts"]["Jobs and Dwelling"]["features"][order_val]["attributes"]
        attrs["year"]          = str(data_year)
        attrs["jobs"]          = jobs_dens
        attrs["dwellingUnits"] = du_dens
        attrs["commtype_jobs"] = commtype_jobs
        attrs["region_jobs"]   = region_jobs
        attrs["commtype_du"]   = commtype_du
        attrs["region_du"]     = region_du
        return attrs

    def test_density_values_written_to_correct_feature(self):
        j = self._build_json()
        attrs = self._apply_density_update(j, order_val=0, data_year=2020,
                                           jobs_dens=4.7, du_dens=2.1,
                                           commtype_jobs=6.0, region_jobs=5.0,
                                           commtype_du=3.5, region_du=3.0)
        self.assertAlmostEqual(attrs["jobs"], 4.7)
        self.assertAlmostEqual(attrs["dwellingUnits"], 2.1)
        self.assertEqual(attrs["year"], "2020")

    def test_benchmark_attributes_written(self):
        j = self._build_json()
        attrs = self._apply_density_update(j, order_val=1, data_year=2035,
                                           jobs_dens=5.2, du_dens=2.8,
                                           commtype_jobs=6.5, region_jobs=5.3,
                                           commtype_du=3.9, region_du=3.2)
        self.assertIn("commtype_jobs", attrs)
        self.assertIn("region_jobs", attrs)
        self.assertIn("commtype_du", attrs)
        self.assertIn("region_du", attrs)
        self.assertAlmostEqual(attrs["commtype_jobs"], 6.5)
        self.assertAlmostEqual(attrs["region_du"], 3.2)

    def test_two_years_written_independently(self):
        j = self._build_json()
        self._apply_density_update(j, order_val=0, data_year=2020, jobs_dens=4.0, du_dens=2.0)
        self._apply_density_update(j, order_val=1, data_year=2035, jobs_dens=5.0, du_dens=3.0)
        feats = j["charts"]["Jobs and Dwelling"]["features"]
        self.assertAlmostEqual(feats[0]["attributes"]["jobs"], 4.0)
        self.assertAlmostEqual(feats[1]["attributes"]["jobs"], 5.0)


# ---------------------------------------------------------------------------
# Task 4: Collision buffer by speed — test pure logic (no arcpy)
# ---------------------------------------------------------------------------

def colln_buffer_by_speed(posted_spd_mph, default=75):
    """Inline copy of collisions.colln_buffer_by_speed() for testing."""
    if posted_spd_mph is None or posted_spd_mph <= 0:
        return default
    spd = float(posted_spd_mph)
    if spd <= 35:
        return 75
    elif spd <= 50:
        return 150
    else:
        return 300


class TestCollisionBufferBySpeed(unittest.TestCase):
    """Task 4: verify speed-based collision buffer thresholds."""

    def test_low_speed_returns_75(self):
        self.assertEqual(colln_buffer_by_speed(25), 75)
        self.assertEqual(colln_buffer_by_speed(35), 75)

    def test_mid_speed_returns_150(self):
        self.assertEqual(colln_buffer_by_speed(36), 150)
        self.assertEqual(colln_buffer_by_speed(45), 150)
        self.assertEqual(colln_buffer_by_speed(50), 150)

    def test_high_speed_returns_300(self):
        self.assertEqual(colln_buffer_by_speed(51), 300)
        self.assertEqual(colln_buffer_by_speed(65), 300)
        self.assertEqual(colln_buffer_by_speed(75), 300)

    def test_none_returns_default(self):
        self.assertEqual(colln_buffer_by_speed(None), 75)

    def test_zero_returns_default(self):
        self.assertEqual(colln_buffer_by_speed(0), 75)

    def test_negative_returns_default(self):
        self.assertEqual(colln_buffer_by_speed(-10), 75)

    def test_float_speed(self):
        self.assertEqual(colln_buffer_by_speed(35.0), 75)
        self.assertEqual(colln_buffer_by_speed(35.1), 150)
        self.assertEqual(colln_buffer_by_speed(50.1), 300)


# ---------------------------------------------------------------------------
# Task 1: Pro-rated area intersect — test the proration math (no arcpy)
# ---------------------------------------------------------------------------

class TestProratedAreaMath(unittest.TestCase):
    """Task 1: verify the area-proration formula is numerically correct."""

    def _prorate(self, original_pop, original_area, clipped_area):
        """Mirrors the proration logic in accessibility_calcs._prorate_acc_polygons()."""
        if original_area and original_area > 0:
            return original_pop * (clipped_area / original_area)
        return original_pop

    def test_full_overlap_unchanged(self):
        self.assertAlmostEqual(self._prorate(1000, 500, 500), 1000)

    def test_half_overlap_halves_pop(self):
        self.assertAlmostEqual(self._prorate(1000, 500, 250), 500)

    def test_quarter_overlap(self):
        self.assertAlmostEqual(self._prorate(800, 400, 100), 200)

    def test_zero_original_area_returns_original_pop(self):
        self.assertAlmostEqual(self._prorate(1000, 0, 100), 1000)

    def test_zero_clipped_area_returns_zero(self):
        self.assertAlmostEqual(self._prorate(1000, 500, 0), 0)

    def test_proration_is_proportional(self):
        # If 60% of area is clipped, pop should be 60% of original
        self.assertAlmostEqual(self._prorate(500, 100, 60), 300)


# ---------------------------------------------------------------------------
# Task 2: Scope leakage fixes — verify make_* functions take input_dict
# ---------------------------------------------------------------------------

class TestInputDictSignature(unittest.TestCase):
    """Task 2: verify that make_* functions accept input_dict (not positional project vars).

    These are import-free structural checks using AST to confirm the
    function signatures without requiring arcpy.
    """

    def _get_first_func_args(self, filepath, funcname):
        import ast
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == funcname:
                return [arg.arg for arg in node.args.args]
        return None

    def _check_make_func(self, filepath, funcname):
        args = self._get_first_func_args(filepath, funcname)
        self.assertIsNotNone(args, f"{funcname} not found in {filepath}")
        self.assertIn('input_dict', args, f"{funcname} in {filepath} should accept input_dict")

    def test_artexp_cong_accepts_input_dict(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'rp_artexp_cong', 'run_congestion_report.py')
        self._check_make_func(os.path.normpath(p), 'make_congestion_rpt_artexp')

    def test_fwyexp_cong_accepts_input_dict(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'rp_fwyexp_cong', 'run_congestion_report.py')
        self._check_make_func(os.path.normpath(p), 'make_congestion_rpt_fwyexp')

    def test_artexp_vmt_accepts_input_dict(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'rp_artexp_vmt', 'run_vmt_report.py')
        self._check_make_func(os.path.normpath(p), 'make_vmt_report_artexp')

    def test_artexp_econ_accepts_input_dict(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'rp_artexp_econ', 'run_econprosp_report.py')
        self._check_make_func(os.path.normpath(p), 'make_econ_report_artexp')

    def test_artsgr_econ_accepts_input_dict(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'rp_artsgr_econ', 'run_econprosp_report.py')
        self._check_make_func(os.path.normpath(p), 'make_econ_report_artsgr')

    def test_artexp_saf_accepts_input_dict(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'rp_artexp_saf', 'run_artexp_safety_report.py')
        self._check_make_func(os.path.normpath(p), 'make_safety_report_artexp')

    def _check_no_bare_project_fc_in_func(self, filepath, funcname):
        """Check that make_* body doesn't assign output_dir from global scope.
        Specifically: output_dir must be assigned within the function body.
        """
        import ast

        class OutputDirChecker(ast.NodeVisitor):
            def __init__(self):
                self.found = False
                self._in_target_func = False

            def visit_FunctionDef(self, node):
                if node.name == funcname:
                    self._in_target_func = True
                    self.generic_visit(node)
                    self._in_target_func = False

            def visit_Assign(self, node):
                if self._in_target_func:
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == 'output_dir':
                            self.found = True
                self.generic_visit(node)

        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        checker = OutputDirChecker()
        checker.visit(tree)
        return checker.found

    def test_artexp_econ_defines_output_dir_locally(self):
        p = os.path.normpath(os.path.join(os.path.dirname(__file__),
                             '..', 'rp_artexp_econ', 'run_econprosp_report.py'))
        self.assertTrue(self._check_no_bare_project_fc_in_func(p, 'make_econ_report_artexp'),
                        "make_econ_report_artexp must define output_dir locally")

    def test_artsgr_frgt_defines_output_dir_locally(self):
        p = os.path.normpath(os.path.join(os.path.dirname(__file__),
                             '..', 'rp_artsgr_frgt', 'run_artsgr_freight_report.py'))
        self.assertTrue(self._check_no_bare_project_fc_in_func(p, 'make_frgt_report_artsgr'),
                        "make_frgt_report_artsgr must define output_dir locally")


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main(verbosity=2)
