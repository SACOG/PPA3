"""
Name: delete_db_projects.py
Purpose: Based on user-entered criteria, this script will delete projects from all PPA log database tables


Author: Darren Conly
Last Updated: Oct 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import arcpy
arcpy.env.overwriteOutput = True

def delete_projects(fgdb, master_tbl, f_uid, subreport_tbls, sql_str):
    # set workspace
    arcpy.env.workspace = fgdb

    # identify which project UID(s) will be deleted. This will based on running a query on the project_master table,
    # and returning a list of UID(s)

    uids_to_delete = []
    with arcpy.da.SearchCursor(master_tbl, field_names=[f_uid], where_clause=sql_str) as cur:
        for row in cur:
            uid = row[0]
            uids_to_delete.append(uid)


    # with list of UID(s) go through all subreport tables and delete all rows in subreport tables where
    # UID is in the list of UIDs to delete

    if len(uids_to_delete) == 0:
        user_entered_uid = input(f"query {sql_str} returned no values. Please enter a UID value you wish to search for or hit Ctrl+c to quit: ")
        uids_to_delete.append(user_entered_uid)

    t_uids_to_delete = tuple(uids_to_delete) if len(uids_to_delete) > 1 else f"('{uids_to_delete[0]}')"
    sql_get_uids = f"{f_uid} IN {t_uids_to_delete}"

    for table in subreport_tbls:
        arcpy.AddMessage(f"Deleting UIDs {t_uids_to_delete} from {table}...")
        tblview = f"fl_{table}"
        arcpy.management.MakeTableView(table, tblview)
        # import pdb; pdb.set_trace()
        arcpy.SelectLayerByAttribute_management(tblview, "NEW_SELECTION", sql_get_uids)

        if int(arcpy.GetCount_management(tblview)[0]) > 0:
            arcpy.DeleteRows_management(tblview)

    # lastly, delete those records from the project master feature class
    fl_project_master = f"fl_{master_tbl}"
    arcpy.management.MakeFeatureLayer(master_tbl, fl_project_master)
    arcpy.SelectLayerByAttribute_management(fl_project_master, "NEW_SELECTION", sql_get_uids)

    if int(arcpy.GetCount_management(fl_project_master)[0]) > 0:
        arcpy.DeleteRows_management(fl_project_master)

if __name__ == '__main__':
    log_tbl_fgdb = r'\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb'
    master_fc = 'project_master'
    uid_field = 'project_uid'

    sql = "project_uid = 'UID_NOT_FOUND'"

    subreport_tables = ['rp_artexp_vmt', 'rp_artexp_econ', 'rp_artexp_eq', 
        'rp_artexp_mm', 'rp_artexp_sgr', 'rp_fwy_vmt', 'rp_fwy_cong', 
        'rp_fwy_mm', 'rp_fwy_econ', 'rp_fwy_frgt', 'rp_fwy_saf', 'rp_artsgr_sgr', 
        'cd_compactdev', 'cd_mixeduse', 'cd_houschoice', 'cd_naturpres', 
        'rp_artexp_cong', 'rp_artexp_frgt', 'rp_artexp_saf', 'cd_trnchoice', 
        'cd_existgasset']


    delete_projects(fgdb=log_tbl_fgdb, master_tbl=master_fc, f_uid=uid_field, 
                    subreport_tbls=subreport_tables, sql_str=sql)