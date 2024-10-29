"""
Name: truncate_tables.py
Purpose: for a fresh/empty set of tables for each funding round, do following:
    1 - ARCHIVE the rollup tables as a copy
    2 - Run this script to truncate the tables (remove all rows but not delete)


Author: Darren Conly
Last Updated: Oct 2024
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import arcpy

def truncate_tables(workspace, tbl_list=None):
    arcpy.env.workspace = workspace

    if tbl_list is None: # if not specified, then truncate *ALL* tables in GDB
        tables = arcpy.ListTables()
        fcs = arcpy.ListFeatureClasses()
        tbl_list = tables + fcs

    for t in tbl_list:
        arcpy.management.TruncateTable(t)
        print(f'Deleted all rows from {t}.')





if __name__ == '__main__':
    wkspc = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb'
    truncate_tables(wkspc, tbl_list=None)