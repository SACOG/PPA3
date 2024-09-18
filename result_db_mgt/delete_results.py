"""
Name: delete_results.py
Purpose: 
    Tool that clears out PPA run results from relevant file GDB tables to free up space and clear
    out clutter associated with testing, etc.

Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

"""
pseudo code:
User enters selection query to identify which projects to delete (e.g. "where proj_name = 'test'" to delete all test projects)
Select all rows in project_master table that match query, get list of project_uid values representing projects to delete
Iterate through all result tables. for each table:
    select all rows where project_uid is in the uid list of projects to delete
    delete those rows

"""

import arcpy

def clear_out_old_projects(fgdb, query_str):
    arcpy.env.workspace = fgdb
    fc_projmaster = 'project_master'
    f_uid = 'project_uid'

    # add safeguard to ensure project actually reviewed for funding program do not get deleted
    query_str = f"{query_str} AND for_review <> 1"

    # get list of uids representing proejcts you want to delete
    uids_to_delete = []
    with arcpy.da.SearchCursor(in_table=fc_projmaster, where_clause=query_str, field_names=[f_uid]) as cur:
        for row in cur:
            uid = row[0]
            uids_to_delete.append(uid)

    print(f"deleting results for {len(uids_to_delete)} projects.")

    tbl_list = [fc_projmaster, *arcpy.ListTables()] # list of tables you want to clear out projects from

    # build query to specify which rows in each table you want to delete
    if len(uids_to_delete) > 1:
        qstr = f"{f_uid} IN {tuple(uids_to_delete)}"
    elif len(uids_to_delete) == 1:
        qstr = f"{f_uid} = {uids_to_delete[0]}"
    else:
        qstr = ""

    # iterate through tables and delete rows where project UID has match in uids_to_delete list
    if qstr != "":
        for tbl in tbl_list:
            tblfields = [f.name for f in arcpy.ListFields(tbl)]
            if f_uid in tblfields:
                with arcpy.da.UpdateCursor(tbl, field_names="*", where_clause=qstr) as ucur:
                    for row in ucur:
                        ucur.deleteRow()
            else:
                print(f"Field {f_uid} not found in {tbl} table. Skipping to next table...")
    print("cleanup completed!")


if __name__ == '__main__':
    query_to_delete = "proj_name = 'test' OR juris = 'test' OR user_email IN ('yongzhi.yu@vertigis.com', 'jhong@sacog.org')"
    result_gdb = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb'

    clear_out_old_projects(fgdb=result_gdb, query_str=query_to_delete)
