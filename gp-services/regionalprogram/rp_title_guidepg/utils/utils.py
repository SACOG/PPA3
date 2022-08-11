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
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import pandas as pd
import arcpy

import parameters as params


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
    '''converts esri gdb table, feature class, feature layer, or SHP to pandas dataframe'''
    data_rows = []
    with arcpy.da.SearchCursor(in_esri_obj, esri_obj_fields) as cur:
        for row in cur:
            out_row = list(row)
            data_rows.append(out_row)

    out_df = pd.DataFrame(data_rows, index=index_field, columns=esri_obj_fields)
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
        row_id = cur.insertRow(data_values)

    arcpy.AddMessage(f"Logged subreport values to {dest_table}")

    return row_id


if __name__ == '__main__':
    print("Script contains functions only. Do not run this as standalone script.")





