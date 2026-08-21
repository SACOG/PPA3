"""
build_test_gdb.py — one-time / refresh export of PPA3 inputs into a local sandbox.
READ-ONLY against the live SDE. Idempotent: re-run to refresh (overwrites local copies).
Run with the ArcGIS Pro python:
  "...\\arcgispro-py3\\python.exe" testing\\local_env\\build_test_gdb.py
"""
import os
import shutil
import argparse
import arcpy
from manifest import SHARED_FCS
import config
import line_registry

# ---- source (prod, read-only) ----
SDE = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\owner_PPA.sde"
SRC_TIF = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\access_tif"
SRC_CSV = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\CSV\Agg_ppa_vals_latest.csv"
SRC_CSV_DIR = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\CSV"  # all reference CSVs (map_img_config, mix_idx_params, ...)
SRC_JSON = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\JSON"
REPO_PARAMS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "gp-services", "regionalprogram", "globalconfig_rp", "parameters.py",
)

# ---- destination (local sandbox) ----
ROOT = str(config.local_root())
GDB = os.path.join(ROOT, "PPA3Testing.gdb")
RUN_GDB = os.path.join(ROOT, "PPA3Testing_run.gdb")
DST_TIF = os.path.join(ROOT, "access_tif")
DST_JSON = os.path.join(ROOT, "json_templates")
CFG_DIR = os.path.join(ROOT, "globalconfig")


def configure_root(root):
    global ROOT, GDB, RUN_GDB, DST_TIF, DST_JSON, CFG_DIR
    ROOT = os.path.abspath(root)
    GDB = os.path.join(ROOT, "PPA3Testing.gdb")
    RUN_GDB = os.path.join(ROOT, "PPA3Testing_run.gdb")
    DST_TIF = os.path.join(ROOT, "access_tif")
    DST_JSON = os.path.join(ROOT, "json_templates")
    CFG_DIR = os.path.join(ROOT, "globalconfig")


def ensure_gdb(path):
    if not arcpy.Exists(path):
        arcpy.management.CreateFileGDB(os.path.dirname(path), os.path.basename(path))


def export_fcs():
    ensure_gdb(GDB)
    arcpy.env.workspace = SDE
    for name in SHARED_FCS:
        src = os.path.join(SDE, name)
        if not arcpy.Exists(src):
            print(f"  !! MISSING in SDE, skipped: {name}")
            continue
        dst = os.path.join(GDB, name)
        if arcpy.Exists(dst):
            arcpy.management.Delete(dst)
        arcpy.conversion.ExportFeatures(src, dst)
        n = int(arcpy.management.GetCount(dst)[0])
        print(f"  copied {name}  ({n} rows)")


def stage_candidate_lines(source_override=None):
    """Copy selectable project geometry into the sandbox so daily runs never depend on I:."""
    for key, entry in line_registry.load(ROOT).items():
        src = source_override or entry.get("source_path")
        dst = entry["fc_path"]
        if arcpy.Exists(dst):
            arcpy.management.Delete(dst)
        if not src or not arcpy.Exists(src):
            raise RuntimeError(
                f"Candidate source for {key} was not found: {src}. "
                "Map I: or pass --candidate-source with a line feature class."
            )
        arcpy.conversion.ExportFeatures(src, dst)
        count = int(arcpy.management.GetCount(dst)[0])
        if count < 1:
            raise RuntimeError(f"Candidate line {key} copied successfully but contains no features")
        print(f"  staged candidate {key} ({count} rows) -> {dst}")


def copy_files():
    os.makedirs(ROOT, exist_ok=True)
    # rasters
    if os.path.isdir(DST_TIF):
        config.assert_within_root(DST_TIF, ROOT)
        shutil.rmtree(DST_TIF)
    shutil.copytree(SRC_TIF, DST_TIF)
    # benchmark csv
    shutil.copy2(SRC_CSV, os.path.join(ROOT, "Agg_ppa_vals_latest.csv"))
    # json templates
    if os.path.isdir(DST_JSON):
        config.assert_within_root(DST_JSON, ROOT)
        shutil.rmtree(DST_JSON)
    shutil.copytree(SRC_JSON, DST_JSON)


def stage_globalconfig():
    os.makedirs(CFG_DIR, exist_ok=True)
    # verbatim copy of parameters.py — logic identical to prod
    shutil.copy2(REPO_PARAMS, os.path.join(CFG_DIR, "parameters.py"))
    # local-pathed data_paths.yaml. rootdir + gisdir + dir_csv are arranged so that
    # parameters.py builds: fgdb->PPA3Testing.gdb, log_fgdb->PPA3Testing_run.gdb,
    # aggval_csv->ROOT\CSV\... (dir_regpgm: .), tifdir->ROOT\access_tif.
    yaml_text = f"""sde:
  path: {GDB}
  region_fc: sacog_region
  fc_speed_data: NPMRDS_2023ppadata_final
  collisions_fc: Collisions2019to2023
  trn_svc_fc: transit_activity_weekdays2024
  freight_route_fc: STAATruckRoutes
  intersections_base_fc: intersections_2024
  comm_types_fc: comm_type_jurspec_dissolve
  reg_centerline_fc: RegionalCenterline_2024
  reg_artcollcline_fc: OSM_ArterialCollector_2022
  reg_bikeway_fc: BikeRte_C1_C2_C4_2024
  proj_line_template_fc: Project_Line_Template

server_data:
  rootdir: {ROOT}
  gisdir:
    dir_name: .
    archived_run_db: PPA3Testing_run.gdb
    svc_root_url: [https://services.sacog.org/gisppa/rest/directories/arcgisjobs]
  dir_commd: CommunityDesign
  dir_regpgm: .
  dir_csv: CSV
  dir_json_template: json_templates

access_data:
  tifdir: {DST_TIF}
  wts:
    pop: pop2020.tif
    workers: workers2020.tif
  acc_lyrs:
    emp:
      transit: transit_jobs_2020.tif
      bike: bike_jobs_2020.tif
      walk: walk_jobs_2020.tif
      drive: drive_jobs_2020.tif
    edu:
      transit: transit_edu_2024.tif
      bike: bike_edu_2024.tif
      walk: walk_edu_2024.tif
      drive: null
    nonwork:
      transit: transit_svcs_2024.tif
      bike: bike_svcs_2024.tif
      walk: walk_svcs_2024.tif
      drive: null
"""
    with open(os.path.join(CFG_DIR, "data_paths.yaml"), "w") as f:
        f.write(yaml_text)
    # stage the CSVs where parameters.py expects them: rootdir\.\CSV\
    # Copy ALL reference CSVs from the prod CSV folder (Agg_ppa_vals_latest, map_img_config,
    # mix_idx_params, ...), not just the benchmark file — the subreports read several of them.
    csv_dir = os.path.join(ROOT, "CSV")
    os.makedirs(csv_dir, exist_ok=True)
    for fn in os.listdir(SRC_CSV_DIR):
        if fn.lower().endswith(".csv"):
            shutil.copy2(os.path.join(SRC_CSV_DIR, fn), os.path.join(csv_dir, fn))


def report_sizes():
    def mb(path):
        total = 0
        for dp, _, fns in os.walk(path):
            for fn in fns:
                total += os.path.getsize(os.path.join(dp, fn))
        return total / (1024 * 1024)
    print(f"\nPPA3Testing.gdb  = {mb(GDB):.1f} MB")
    print(f"access_tif       = {mb(DST_TIF):.1f} MB")
    print(f"total C:\\PPA3Testing = {mb(ROOT):.1f} MB")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="local sandbox root")
    parser.add_argument(
        "--candidate-source",
        help="optional feature-class path to use instead of the registry's candidate source",
    )
    args = parser.parse_args(argv)
    configure_root(args.root)
    os.makedirs(ROOT, exist_ok=True)  # must exist before CreateFileGDB runs in export_fcs()
    print("Exporting shared feature classes (read-only from SDE)...")
    export_fcs()
    stage_candidate_lines(args.candidate_source)
    print("Copying rasters, CSV, JSON templates...")
    copy_files()
    print("Staging local globalconfig...")
    ensure_gdb(RUN_GDB)
    stage_globalconfig()
    report_sizes()
    print(f"\nDone. Local test root ready at {ROOT}")


if __name__ == "__main__":
    main()
