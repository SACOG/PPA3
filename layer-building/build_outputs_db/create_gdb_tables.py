"""
Name: create_db_table.py
Purpose: 
    create table in file GDB or SDE with fields and data types specified by input CSV file
    which specifies: TableName,	FieldName,	esri_dtype,	max_field_len, use_table_indicator


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from datetime import datetime as dt

import arcpy
import pandas as pd

def build_db_tables(gdb_workspace, spec_csv, tables_to_make=[]):
    arcpy.env.workspace = gdb_workspace
    time_stamp = str(dt.now().strftime('%Y%m%d%H%M'))

    f_tblname = 'TableName'
    f_fieldname = 'FieldName'
    f_geomtyp = 'geom_type'
    f_dtype = 'esri_dtype'
    f_len = 'text_len'
    f_usetable = 'use_table'

    dtype_shape = 'SHAPE'

    # load master CSV with table names, field names, field dtypes for all tables
    df_master = pd.read_csv(spec_csv, usecols=[f_tblname, f_usetable, f_geomtyp, f_fieldname, f_dtype, f_len])


    # filter to only work with tables where use_table is true (master table may have proposed future tables)
    
    df_master = df_master.loc[df_master[f_usetable] == 1]
    
    # if user specifies list of tables, then further filter to only specify those table names;
    if len(tables_to_make) > 0:
        df_master = df_master.loc[df_master[f_tblname].isin(tables_to_make)]
        

    tables_to_create = df_master[f_tblname].unique()


# iterate through each unique table name. For each unique table name:
    for table in tables_to_create:

        # if table name already exists in database: warn user that table already exists and that existing table will be renamed to <tablename>_yyyymmddhhmm and
        if arcpy.Exists(table):
            arcpy.AddMessage(f"{table} already exists. Existing version will be renamed as {table}_{time_stamp}.")
            arcpy.management.Rename(table, f"{table}_{time_stamp}")
    
        # select rows in master table with that table name
        dft = df_master.loc[df_master[f_tblname] == table]

        # if any of that table's fields have dtype='SHAPE', then make table as feature class, otherwise make it as non-spatial table
        if dtype_shape in dft[f_dtype].values:
            geom_type = dft[f_geomtyp][0] # polyline, point, polygon, etc.
            sr_web_mercator = arcpy.SpatialReference(3857)
            arcpy.management.CreateFeatureclass(gdb_workspace, table, geometry_type=geom_type, spatial_reference=sr_web_mercator)
        else:
            arcpy.management.CreateTable(gdb_workspace, table)

        # convert subset table into dict for field info using df.to_dict(orient='records')
        tbl_dict = dft.to_dict(orient='records')

        for drow in tbl_dict:
            try:
                text_len = int(drow[f_len]) if f_dtype == 'TEXT' else None
                if drow[f_dtype] == dtype_shape: # arcpy automatically adds SHAPE/geo field when creating feature class, so don't add explicitly
                    continue

                arcpy.management.AddField(table, drow[f_fieldname], drow[f_dtype], field_length=text_len)
            except:
                import pdb; pdb.set_trace()

        arcpy.AddMessage(f"created table {table}")



if __name__ == '__main__':
    fgdb = r'\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb'
    config_csv = r'C:\Users\dconly\GitRepos\PPA3\layer-building\build_outputs_db\output_db_tables_test.csv'
    make_tables = [] # ['project_master', 'rp_artexp_cong']

    build_db_tables(gdb_workspace=fgdb, spec_csv=config_csv, tables_to_make=make_tables)