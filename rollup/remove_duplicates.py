"""
Name: remove_duplicates.py
Purpose: iterates through all rollup data tables and removes duplicate instances of project_uid values.
    To remove duplicates, it keeps only the row for each project_uid value with the lowest corresponding OBJECTID value


Author: Darren Conly
Last Updated: Oct 2024
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path

import pandas as pd
import arcpy

def delete_dupe_uids(in_tbl):
    f_oid = 'OBJECTID'
    f_uid = 'project_uid'
    tname = Path(in_tbl).name
    
    # get dict with {uid: lowest OBJECTID value} for uids that have more than one row in table
    uid_list = {}
    fields = [f_oid, f_uid]
    all_tbl_fields = [f.name for f in arcpy.ListFields(in_tbl)]
    missing_fields = [f for f in fields if f not in all_tbl_fields]
    
    if len(missing_fields) == 0:
        with arcpy.da.SearchCursor(in_tbl, field_names=fields) as scur:
            for row in scur:
                oid = row[fields.index(f_oid)]
                uid = row[fields.index(f_uid)]
                if not uid_list.get(uid):
                    uid_list[uid] = [oid]
                else:
                    uid_list[uid] = uid_list[uid] + [oid]

        # delete rows for each UID if the OID is not the lowest OID for that UID
        rows_deleted = 0
        with arcpy.da.UpdateCursor(in_tbl, field_names=fields) as ucur:
            for row in ucur:
                oid = row[fields.index(f_oid)]
                uid = row[fields.index(f_uid)]
                min_oid = min(uid_list[uid])

                if oid != min_oid:
                    ucur.deleteRow()
                    rows_deleted += 1

        print(f"{rows_deleted} rows deleted from {tname}")
    else:
        print(f"WARNING: fields {missing_fields} not found in {tname}")
    
if __name__ == '__main__':
    #================================RUN FUNC========================    
    fgdb = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb'

    arcpy.env.workspace = fgdb
    for t in arcpy.ListTables():
        delete_dupe_uids(t)