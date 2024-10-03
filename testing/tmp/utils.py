# --------------------------------
# Name: utils.py
# Purpose: Provides general PPA functions that are used throughout various PPA scripts and are not specific to any one PPA script
#
# #
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import pandas as pd
import arcpy


# NOTE - this must be copy/pasted into the script it will be used in, otherwise it will reference the wrong script in the traceback message.
def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # script name + line number
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe())
    # Get Python syntax error
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

    
def remove_forbidden_chars(in_str):
    '''Replaces forbidden characters with acceptable characters'''
    repldict = {"&":'And','%':'pct','/':'-'}
    
    for old, new in repldict.items():
        if old in in_str:
            out_str = in_str.replace(old, new)
        else:
            out_str = in_str
    
    return out_str
    
    
def esri_field_exists(in_tbl, field_name):
    fields = [f.name for f in arcpy.ListFields(in_tbl)]
    if field_name in fields:
        return True
    else:
        return False


def esri_object_to_df(in_esri_obj, esri_obj_fields, index_field=None):
    '''
    WARNING 7/3/2024 - DEPRECATED VERSION. INSTEAD USE esri_to_df function below.
    converts esri gdb table, feature class, feature layer, or SHP to pandas dataframe'''

    data_rows = []
    with arcpy.da.SearchCursor(in_esri_obj, esri_obj_fields) as cur:
        for row in cur:
            out_row = list(row)
            data_rows.append(out_row)

    out_df = pd.DataFrame(data_rows, index=index_field, columns=esri_obj_fields)
    return out_df

def esri_to_df(esri_obj_path, include_geom, field_list=None, index_field=None, 
               crs_val=None, dissolve=False):
    """
    Converts ESRI file (File GDB table, SHP, or feature class) to either pandas dataframe
    or geopandas geodataframe (if it is spatial data)
    esri_obj_path = path to ESRI file
    include_geom = True/False on whether you want resulting table to have spatial data (only possible if
        input file is spatial)
    field_list = list of fields you want to load. No need to specify geometry field name as will be added automatically
        if you select include_geom. Optional. By default all fields load.
    index_field = if you want to choose a pre-existing field for the dataframe index. Optional.
    crs_val = crs, in geopandas CRS string format, that you want to apply to the resulting geodataframe. Optional.
    dissolve = True/False indicating if you want the resulting GDF to be dissolved to single feature.
    """

    fields = field_list # should not be necessary, but was having issues where class properties were getting changed with this formula
    if not field_list:
        fields = [f.name for f in arcpy.ListFields(esri_obj_path)]

    if include_geom:
        import geopandas as gpd
        from shapely import wkt
        # by convention, geopandas uses 'geometry' instead of 'SHAPE@' for geom field
        f_esrishp = 'SHAPE@'
        f_gpdshape = 'geometry'
        fields = fields + [f_esrishp]

    data_rows = []
    with arcpy.da.SearchCursor(esri_obj_path, fields) as cur:
        for row in cur:
            rowlist = [i for i in row]
            if include_geom:
                geom_wkt = wkt.loads(rowlist[fields.index(f_esrishp)].WKT)
                rowlist[fields.index(f_esrishp)] = geom_wkt
            out_row = rowlist
            data_rows.append(out_row)  

    if include_geom:
        fields_gpd = [f for f in fields]
        fields_gpd[fields_gpd.index(f_esrishp)] = f_gpdshape
        
        out_df = gpd.GeoDataFrame(data_rows, columns=fields_gpd, geometry=f_gpdshape)

        # only set if the input file has no CRS--this is not same thing as .to_crs(), which merely projects to a CRS
        if crs_val: out_df.crs = crs_val

        # dissolve to single zone so that, during spatial join, points don't erroneously tag to 2 overlapping zones.
        if dissolve and out_df.shape[0] > 1: 
            out_df = out_df.dissolve() 
    else:
        out_df = pd.DataFrame(data_rows, index=index_field, columns=field_list)

    return out_df
    
    
def rename_dict_keys(dict_in, new_key_dict):
    '''if dict in = {0:1} and dict out supposed to be {'zero':1}, this function renames the key accordingly per
    the new_key_dict (which for this example would be {0:'zero'}'''
    dict_out = {}
    for k, v in new_key_dict.items():
        if k in list(dict_in.keys()):
            dict_out[v] = dict_in[k]
        else:
            dict_out[v] = 0
    return dict_out


def log_row_to_table(data_row_dict, dest_table):
    """Writes row of values to table. Fields are data_row_dict keys, and the values
    written are the values from data_row_dict's values."""

    data_fields = list(data_row_dict.keys())
    data_values = list(data_row_dict.values())

    with arcpy.da.InsertCursor(dest_table, data_fields) as cur:
        cur.insertRow(data_values)

    arcpy.AddMessage(f"Logged subreport values to {dest_table}")

def get_project_uid(proj_name, proj_type, proj_jur, user_email):
    """Find the project UID in the master table where project name, type, 
    and user email match and it's the most recently-run one"""

    master_fields = [params.logtbl_join_key, params.f_master_tstamp]

    fc_mastertbl = os.path.join(params.log_fgdb, params.log_master)
    fl_mastertbl = 'fl_mastertbl'
    arcpy.MakeFeatureLayer_management(fc_mastertbl, fl_mastertbl)

    sql = f"""{params.f_master_projname} = '{proj_name}' AND {params.f_master_projtyp} = '{proj_type}'
    AND {params.f_master_jur} = '{proj_jur}' AND {params.f_master_email} = '{user_email}'"""

    arcpy.AddMessage(f"Finding project UID via {sql} in table {fc_mastertbl}")
    
    arcpy.management.SelectLayerByAttribute(fl_mastertbl, "NEW_SELECTION", sql)

    df = esri_object_to_df(fl_mastertbl, esri_obj_fields=master_fields, index_field=None)

    if df.shape[0] == 0:
        uid = "UID_NOT_FOUND"
        arcpy.AddWarning(f"No project records found in {fc_mastertbl} where {sql}")
    else:
        uid = df.sort_values(by=params.f_master_tstamp, ascending=False) \
            [params.logtbl_join_key][0]

    return uid


if __name__ == '__main__':
    print("Script contains functions only. Do not run this as standalone script.")





