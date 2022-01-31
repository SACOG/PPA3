#!/usr/bin/env python
# coding: utf-8

# In[26]:


"""
Approach:
1 - load all numbers from all reports
2 - line-by-line, digit-by-digit populating of JSON file
3 - get it to work, refactor later as needed.
"""
import datetime as dt
from time import perf_counter as perf
import os
import json
import pandas as pd
import arcpy
arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

import base_scripts.ppa_input_params as params
from base_scripts.npmrds_data_conflation import get_npmrds_data


# identify project community type
def get_proj_ctype(in_project_fc, commtypes_fc):
    '''Get project community type, based on which community type has most spatial overlap with project'''
    ts = int(perf())
    temp_intersect_fc = os.path.join(arcpy.env.scratchGDB, f'temp_intersect_fc{ts}')
    if arcpy.Exists(temp_intersect_fc): arcpy.Delete_management(temp_intersect_fc)
    arcpy.Intersect_analysis([in_project_fc, commtypes_fc], temp_intersect_fc, "ALL", 
                             0, "LINE")
    
    # debugging messages to find out why ctype tagging intermittently fails
    intersect_cnt = int(arcpy.GetCount_management(temp_intersect_fc)[0])
    in_project_cnt = int(arcpy.GetCount_management(in_project_fc)[0])
    arcpy.AddMessage("project line feature count: {}".format(in_project_cnt))
    arcpy.AddMessage("Project segments after intersecting with comm types: {}".format(intersect_cnt))
    
    len_field = 'SHAPE@LENGTH'
    fields = ['OBJECTID', len_field, params.col_ctype]
    ctype_dist_dict = {}
    
    with arcpy.da.SearchCursor(temp_intersect_fc, fields) as cur:
        for row in cur:
            ctype = row[fields.index(params.col_ctype)]
            seg_len = row[fields.index(len_field)]
        
            if ctype_dist_dict.get(ctype) is None:
                ctype_dist_dict[ctype] = seg_len
            else:
                ctype_dist_dict[ctype] += seg_len
    try:
        maxval = max([v for k, v in ctype_dist_dict.items()])
        proj_ctype = [k for k, v in ctype_dist_dict.items() if v == maxval][0]

        return proj_ctype
    except:
        raise ValueError("ERROR: No Community Type identified for project. \n{} project line features." \
        " {} features in intersect layer.".format(in_project_cnt, in_project_cnt))

def data_dirn_name(in_data_key):
    # converts, for example "NORTHBOUNDsomething_else" to just be "NORTHBOUND"
    return f"{in_data_key.split('BOUND')[0]}BOUND"



if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============
    # load json template
    in_json = r"C:\Users\dconly\GitRepos\PPA3\testing\json_template\SACOG_ReduceCongestion_template.json"
    with open(in_json, "r") as j_in:
        json_loaded = json.load(j_in)

    output_dir = os.path.join(r"C:\Users\dconly\GitRepos\PPA3\testing\json_output")


    # specify project line feature class and attributes
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\PPAClientRun_SacCity_StocktonBl'
    project_name = "StocktonBl"
    project_aadt = 23000

    ptype = params.ptype_arterial

    # csv table of aggregate values
    aggval_csv = r"C:\Users\dconly\GitRepos\PPA3\testing\base_scripts\Agg_ppa_vals04222020_1017.csv"

    #============SELDOM-CHANGED INPUTS===================
    # re-used json keys, so assign to variable
    k_charts = "charts"
    k_title = "title"
    k_features = "features" # remember, this is a list of dicts
    k_attrs = "attributes"
    k_year = "year"
    k_type = "type"
    k_congnratio = "congestionRatio"
    k_congncharts = "Free flow vs Congested Speeds"
    k_reliabcharts = "Travel Time Reliability Index"

    # lookups to rename directions for charts in case you need shorter labels (2 chars instead of 9+ chars)
    # dirn_dict = {"NB":"NORTHBOUND", "SB":"SOUTHBOUND", "EB":"EASTBOUND", "WB":"WESTBOUND"}
    # dirn_dict_rev = {v:k for k, v in dirn_dict.items()}

    # name conversion between the keys of the dictionary containing the output data and the labels used in the charts.
    cong_name_lookup = {"freeFlowSpeed":params.col_ff_speed, "averageCongestedSpeed":params.col_congest_speed}
    ttr_name_lookup = {"AMPeakTTR":params.col_reliab_ampk, "PMPeakTTR":params.col_reliab_pmpk, 
                        "middayTTR":params.col_reliab_md, "weekendTTR":params.col_reliab_wknd}
    ttr_name_lookup_rev = {v:k for k, v in ttr_name_lookup.items()}

    #=================BEGIN SCRIPT===========================

    # =====================update AADT data
    json_loaded["projectAADT"] = project_aadt

    # ========================calc all congestion values
    cong_data = get_npmrds_data(project_fc, ptype)
    data_keys = list(cong_data.keys())

    # get unique direction names, sorted to ensure consistent order in all charts
    # example output ["NORTHBOUND", "SOUTHBOUND"]
    data_directions = sorted(list(set([data_dirn_name(i) for i in data_keys])))

    # reset the congestionRatio table labels so you can reset the direction names
    json_loaded[k_congnratio] = {}

    
    for i, direcn in enumerate(data_directions):
        dirn_data = {k:v for k, v in cong_data.items() if direcn in k} # get only data for the indicated direction
        ddata2 = {f"{k.split('BOUND')[1]}":v for k, v in dirn_data.items()} # strip direction from the data keys, since we already filtered for it
        # example: turns {"NORTHBOUNDsome_metric":...} into {"some_metric":...}

        # dir_chartlabel = dirn_dict_rev[direcn] # gets the direction name that will appear on charts--CONSIDER JUST USING THE KEYS' direction

        cong_speed = ddata2[params.col_congest_speed]
        ff_speed = ddata2[params.col_ff_speed]

        # ----------populate congestion ratio for each direction
        cong_ratio = cong_speed / ff_speed
        json_loaded[k_congnratio][direcn] = cong_ratio

        #-----------get FF and congested speed numbers for both directions
        json_loaded[k_charts][k_congncharts][k_features][i][k_attrs][k_type] = direcn
        json_loaded[k_charts][k_congncharts][k_features][i][k_attrs]["averageCongestedSpeed"] = cong_speed
        json_loaded[k_charts][k_congncharts][k_features][i][k_attrs]["freeFlowSpeed"] = ff_speed

        #-----------get travel time reliability ratio for both directions
        json_loaded[k_charts][k_reliabcharts][k_features][i][k_attrs][k_type] = direcn
        for relmet_label, relmet_dkey in ttr_name_lookup.items():
            value = ddata2[relmet_dkey]
            json_loaded[k_charts][k_reliabcharts][k_features][i][k_attrs][relmet_label] = value

    # ============================write out updated json to file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CongestionReport{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    with open(out_file, 'w') as f_out:
        json.dump(json_loaded, f_out, indent=4)
        
    print(f"wrote JSON output to {out_file}")


