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

def clear_tbl(tbl, qry_str, uid_field):
    tblfields = [f.name for f in arcpy.ListFields(tbl)]
    if uid_field in tblfields:
        with arcpy.da.UpdateCursor(tbl, field_names="*", where_clause=qry_str) as ucur:
            for row in ucur:
                ucur.deleteRow()
    else:
        print(f"Field {uid_field} not found in {tbl} table. Skipping to next table...")

def clear_out_old_projects(fgdb, query_str=None, rmv_orphan_uid=True, protect_review_runs=True):
    arcpy.env.workspace = fgdb
    fc_projmaster = 'project_master'
    f_uid = 'project_uid'
    v_orphan_record = 'UID_NOT_FOUND'

    # add safeguard to ensure project actually reviewed for funding program do not get deleted
    if protect_review_runs:
        qs_protect = "for_review <> 1"
        if query_str:
            query_str = f"{query_str} AND {qs_protect}"
        else:
            query_str = qs_protect

    # get list of uids representing proejcts you want to delete
    uids_to_delete = []
    with arcpy.da.SearchCursor(in_table=fc_projmaster, where_clause=query_str, field_names=[f_uid]) as cur:
        for row in cur:
            uid = row[0]
            uids_to_delete.append(uid)

    if rmv_orphan_uid: uids_to_delete.append(v_orphan_record)

    status_msg = f"deleting results for {len(uids_to_delete)} projects"
    if protect_review_runs: status_msg.append('(keeping projects marked for review)')
    print(status_msg)

    tbl_list = [fc_projmaster, *arcpy.ListTables()] # list of tables you want to clear out projects from

    # build query to specify which rows in each table you want to delete
    qstr = None
    if len(uids_to_delete) > 1:
        qstr = f"{f_uid} IN {tuple(uids_to_delete)}"
    elif len(uids_to_delete) == 1:
        qstr = f"{f_uid} = '{uids_to_delete[0]}'"
        

    # iterate through tables and delete rows where project UID has match in uids_to_delete list
    # import pdb; pdb.set_trace()
    if qstr:
        for tbl in tbl_list:
            clear_tbl(tbl, qstr, f_uid)

    projects_left = arcpy.GetCount_management(fc_projmaster)[0]
    print(f"cleanup completed! {projects_left} in {fc_projmaster}")


if __name__ == '__main__':
    # query_to_delete = "proj_name = 'test' OR juris = 'test' OR user_email IN ('yongzhi.yu@vertigis.com', 'jhong@sacog.org')"
    # query_to_delete = """proj_type IN ('TEST', 'test', 'Rehabilitation and Operational Improvements', 
    #                                     'Freeway Expansion', 'Community Design', 'Arterial State of Good Repair',
    #                                     'Arterial or Transit Expansion')"""
    # query_to_delete = "project_uid = 'UID_NOT_FOUND'" # set to None if you want to delete all projects
    query_to_delete = None
    keep_reviewed_runs = True
    
    # result_gdb = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb'
    result_gdb = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data_1.gdb'

    clear_out_old_projects(fgdb=result_gdb, query_str=query_to_delete)
