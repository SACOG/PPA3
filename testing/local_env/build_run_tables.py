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

def main():
    if not arcpy.Exists(LOCAL_RUN_GDB):
        raise SystemExit(f"local run gdb missing: {LOCAL_RUN_GDB} (run build_test_gdb.py first)")
    # Mirror EVERY table + feature class in the prod run gdb as an empty local copy, so we
    # never have to guess archive-table names. The naming is not uniform: arterial log tables
    # are rp_artexp_*/rp_artsgr_*, FREEWAY are rp_fwy_* (NOT rp_fwyexp_*), community design are
    # cd_*, and project_master is a Polyline FeatureClass. The prod gdb is the source of truth.
    arcpy.env.workspace = PROD_RUN_GDB
    names = sorted((arcpy.ListTables() or []) + (arcpy.ListFeatureClasses() or []))
    for name in names:
        src = os.path.join(PROD_RUN_GDB, name)
        dst = os.path.join(LOCAL_RUN_GDB, name)
        if arcpy.Exists(dst):
            arcpy.management.Delete(dst)
        # Create an EMPTY copy that preserves the schema without copying rows. Some archive
        # datasets (project_master) are spatial FeatureClasses whose rows carry SHAPE@ geometry
        # and are read via MakeFeatureLayer, so a plain CreateTable produces an unusable table.
        # Branch on geometry: FeatureClass -> CreateFeatureclass (template + geom + SR); else CreateTable.
        d = arcpy.Describe(src)
        if getattr(d, "shapeType", None):
            arcpy.management.CreateFeatureclass(
                LOCAL_RUN_GDB, name,
                geometry_type=d.shapeType.upper(),
                template=src,
                spatial_reference=d.spatialReference,
            )
            print(f"  created empty FEATURECLASS {name} ({d.shapeType})")
        else:
            arcpy.management.CreateTable(LOCAL_RUN_GDB, name, template=src)
            print(f"  created empty TABLE {name}")
    print(f"Done. Mirrored {len(names)} datasets from prod run gdb.")


if __name__ == "__main__":
    main()
