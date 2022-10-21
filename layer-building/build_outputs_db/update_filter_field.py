"""
Name: update_filter_field.py
Purpose: The project_master log table has a filter field that allows us to know which
    projects we want to include in comparison rollups and which ones we want to exclude.
    E.g., want to exclude test runs.

    This script takes in a list of project UID values and updates the project_master table
    so that each record in the master table is tagged with 1/0 value indicating if it is 
    to be included in rollup charts.


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import arcpy
import pandas as pd

def update_filter_field(fc_in, values_to_update, setval):
    f_project_uid = 'project_uid'
    f_filterflag = 'for_review'

    fields = [f_project_uid, f_filterflag]
    print(f"setting {f_filterflag} to {setval} for {len(values_to_update)} projects...")
    cnt_updated = 0
    not_found = []

    with arcpy.da.UpdateCursor(fc_in, fields) as ucur:
        for row in ucur:
            checkval = row[fields.index(f_project_uid)]
            if checkval in values_to_update:
                row[fields.index(f_filterflag)] = setval
                ucur.updateRow(row)

                cnt_updated += 1

    print(f"Finished updating. {cnt_updated} out of {len(values_to_update)} specified projects were updated.")

    if len(not_found) > 0:
        print(f"The following project UIDs were not found in {fc_in}: {not_found}")


if __name__ == '__main__':
    project_list_csv = r"C:\Users\dconly\GitRepos\PPA3\layer-building\build_outputs_db\test_projects_to_flag.csv"
    project_list = pd.read_csv(project_list_csv)['project_uid'].to_list()

    projlist_uid_field = 'project_uid'

    fc_project_master = r'\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb\project_master'
    val_yes_compare = 1

    update_filter_field(fc_in=fc_project_master, values_to_update=project_list, setval=val_yes_compare)