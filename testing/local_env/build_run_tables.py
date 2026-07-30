"""
build_run_tables.py — OPTIONAL. Read (read-only) the real schemas of project_master and the
rp_* archive tables from the production PPA3_run_data.gdb and create EMPTY copies in the local
PPA3Testing_run.gdb, so a full local run completes cleanly through the archive log-write step.
Read-only against prod; writes only to the local sandbox. Run via PowerShell with the Pro python.
"""
import os
import arcpy

PROD_RUN_GDB = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb"
LOCAL_RUN_GDB = r"C:\PPA3Testing\PPA3Testing_run.gdb"

# tables to mirror: project_master + one per live rp_* service (folder names)
TABLES = [
    "project_master",
    "rp_title_guidepg", "rp_artexp_vmt", "rp_artexp_cong", "rp_artexp_mm", "rp_artexp_econ",
    "rp_artexp_frgt", "rp_artexp_saf", "rp_artsgr_sgr", "rp_artexp_eq",
    "rp_fwyexp_vmt", "rp_fwyexp_cong", "rp_fwyexp_mm", "rp_fwyexp_econ", "rp_fwyexp_frgt",
    "rp_fwyexp_saf",
]


def main():
    if not arcpy.Exists(LOCAL_RUN_GDB):
        raise SystemExit(f"local run gdb missing: {LOCAL_RUN_GDB} (run build_test_gdb.py first)")
    for name in TABLES:
        src = os.path.join(PROD_RUN_GDB, name)
        if not arcpy.Exists(src):
            print(f"  !! not in prod, skipped: {name}")
            continue
        dst = os.path.join(LOCAL_RUN_GDB, name)
        if arcpy.Exists(dst):
            arcpy.management.Delete(dst)
        # Create an EMPTY copy that preserves the schema without copying rows.
        # project_master is a spatial FeatureClass (its rows carry SHAPE@ geometry and it
        # is read via MakeFeatureLayer), so a plain CreateTable produces an unusable table
        # that fails as Input Features / for InsertCursor with SHAPE@. Branch on whether the
        # prod source has geometry: FeatureClass -> CreateFeatureclass (template + geometry
        # type + spatial ref); plain table -> CreateTable.
        d = arcpy.Describe(src)
        if getattr(d, "shapeType", None):
            arcpy.management.CreateFeatureclass(
                LOCAL_RUN_GDB, name,
                geometry_type=d.shapeType.upper(),
                template=src,
                spatial_reference=d.spatialReference,
            )
            print(f"  created empty FEATURECLASS {name} ({d.shapeType}, schema from prod)")
        else:
            arcpy.management.CreateTable(LOCAL_RUN_GDB, name, template=src)
            print(f"  created empty TABLE {name} (schema from prod)")
    print("Done.")


if __name__ == "__main__":
    main()
