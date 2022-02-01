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
# arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

import base_scripts.ppa_input_params as params
from base_scripts.accessibility_calcs import get_acc_data
from base_scripts.mix_index_for_project import get_mix_idx
from base_scripts.landuse_buff_calcs import LandUseBuffCalcs


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

# make dict of region and community type values for specified metric and community type
def make_aggval_dict(aggval_df, metric_cols, proj_ctype, yearval=None):
    
    if yearval:
        aggdatadf_proj = aggval_df.loc[(aggval_df[metname_col].isin(metric_cols)) & \
            (aggval_df[k_year] == yearval)] \
            [[metname_col, project_commtype, geo_region, k_year]]
    else:
        aggdatadf_proj = aggval_df.loc[aggval_df[metname_col].isin(metric_cols)] \
            [[metname_col, project_commtype, geo_region, k_year]]

    agg_dict_list = aggdatadf_proj.to_dict(orient='records')

    aggval_dict = {d[metname_col]:{project_commtype:d[proj_ctype], 
                      geo_region:d[geo_region],
                      k_year:d[k_year]} for d in agg_dict_list}

    return aggval_dict



if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============

    in_json = "SACOG_ReduceVMT_template.json"
    output_dir = arcpy.env.scratchFolder  # os.path.join(r"C:\Users\dconly\GitRepos\PPA3\testing\json_output")


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)  # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\PPAClientRun_SacCity_StocktonBl'
    project_name = arcpy.GetParameterAsText(1)

    ptype = params.ptype_arterial
    data_years = [2016, 2040]


    

    #============SELDOM-CHANGED INPUTS===================

    # names in json template
    geo_project = "Project"
    geo_ctype = "Community Type"
    geo_region = "Region"

    # re-used json keys, so assign to variable
    k_charts = "charts"
    k_features = "features" # remember, this is a list of dicts
    k_attrs = "attributes"
    k_year = "year"
    k_type = "type"

    geographies = [geo_project, geo_ctype, geo_region]

    svr_folder = r'\\arcserver-svr\D\PPA_v2_SVR' # folder registered with server.

    # csv table of aggregate values
    aggval_csv = r"\\arcserver-svr\D\PPA_v2_SVR\PPA2\Input_Template\CSV\Agg_ppa_vals04222020_1017.csv" # os.path.join(svr_folder, 'Input_Template', 'CSV', 'Agg_ppa_vals04222020_1017.csv')
    
    arcpy.env.workspace = params.fgdb # database registered with portal, has data layers that PPA needs

    #=================BEGIN SCRIPT===========================
    
    #==================setting key parameters

    # load json template
    in_json_path = r"\\arcserver-svr\D\PPA_v2_SVR\PPA2\Input_Template\JSON\SACOG_ReduceVMT_template.json" # os.path.join(svr_folder, 'Input_Template', 'JSON', in_json)
    with open(in_json_path, "r") as j_in: # load applicable json template
        json_loaded = json.load(j_in)


    # =======================import CSV of aggregate values as dataframe
    df_agg = pd.read_csv(aggval_csv)
    metname_col = "metric_name"
    df_agg = df_agg.rename(columns={'Unnamed: 0':metname_col, 'REGION': geo_region})

    # ====================get project community type

    project_commtype = get_proj_ctype(project_fc, params.comm_types_fc)

    # ========================calc land use buffer values 
    lu_buffdist_ft = params.ilut_sum_buffdist
    value_fields = ['EMPTOT', 'DU_TOT']

    out_data = {}
    for data_year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(data_year)
        year_dict = LandUseBuffCalcs(in_pcl_pt_fc, project_fc, ptype, value_fields, lu_buffdist_ft).point_sum()
        out_data[data_year] = year_dict
        

    # update applicable field values in JSON template
    for i, year in enumerate(data_years):
        jobs = out_data[year]['EMPTOT']
        du = out_data[year]['DU_TOT']
        json_loaded[k_charts]["Jobs and Dwelling"][k_features][i][k_attrs]['year'] = year
        json_loaded[k_charts]["Jobs and Dwelling"][k_features][i][k_attrs]['jobs'] = jobs
        json_loaded[k_charts]["Jobs and Dwelling"][k_features][i][k_attrs]['dwellingUnits'] = du

    print("calculated buffer values sucessfully")


    # =======================calc accessibility numbers and update JSON chart with it

    fc_accessibility_data = params.accdata_fc

    # project level dict of accessibility script outputs
    dict_data = get_acc_data(project_fc, fc_accessibility_data, ptype) 

    # lookup dict between names of data points in raw output and names in JSON file
    dest_type = 'poi2' # destination type as specified in raw data output
    acc_metrics = {f'WALKDESTS{dest_type}':'30 Min Walk', f'BIKEDESTS{dest_type}':'30 Min Biking', 
                    f'AUTODESTS{dest_type}':'15 Min Drive', f'TRANDESTS{dest_type}':'45 Min Transit'}
    accmetrics_keys = list(acc_metrics.keys())

    # trimmed down output, only containing the accessibility metrics needed for this chart 
    # instead of all accessibility metrics
    dict_data2 = {k:dict_data[k] for k in acc_metrics.keys()}

    # make dict of regional and comm type values
    aggval_dict = make_aggval_dict(df_agg, accmetrics_keys, project_commtype)

    for i, k in enumerate(list(acc_metrics.keys())):
        
        # update value for "type" (mode of tranpsortation)
        json_loaded[k_charts]["Base Year Service Accessibility"][k_features][i] \
            [k_attrs][k_type] = acc_metrics[k]
        
        # update value for mode's access from project
        json_loaded[k_charts]["Base Year Service Accessibility"][k_features][i] \
            [k_attrs][geo_project] = dict_data2[k] 
        
        # update value for mode's access avg for project comm type
        json_loaded[k_charts]["Base Year Service Accessibility"][k_features][i] \
            [k_attrs][geo_ctype] = aggval_dict[k][project_commtype] 
        
        # update value for mode's access avg for region
        json_loaded[k_charts]["Base Year Service Accessibility"][k_features][i] \
            [k_attrs][geo_region] = aggval_dict[k][geo_region] 

    print("calculated accessibility values sucessfully")



    # ==============================calc mix index
    buff_dist_ft = params.mix_index_buffdist  # distance in feet--MIGHT NEED TO BE ADJUSTED FOR WGS 84--SEE OLD TOOL FOR HOW THIS WAS RESOLVED
    metname = 'mix_index'


    # get list of the geography types in the order they appear in the json file
    geotype_keys = []
    for feature in json_loaded[k_charts]["Land Use Diversity"][k_features]:
        geotype_keys.append(feature[k_attrs][k_type])

    out_dict = {}
    for data_year in data_years:
        # get region and ctype values as dict
        aggval_dict = make_aggval_dict(df_agg, ['mix_index'], project_commtype, yearval=data_year)
        output_dict = aggval_dict[metname] # remove the top dimension from the dict
        
        # get project-specific values as dict
        in_pcl_pt_fc = params.parcel_pt_fc_yr(in_year=data_year) # input fc of parcel data--must be points!
        project_dict = get_mix_idx(in_pcl_pt_fc, project_fc, ptype)
        output_dict[geo_project] = project_dict[metname] # add project-level data to dict with region and ctype vals
        output_dict[geo_ctype] = output_dict[project_commtype]

        year_label = f"diversity {data_year}"
        for i, geo_type in enumerate(geotype_keys):
            json_loaded[k_charts]["Land Use Diversity"][k_features][i][k_attrs][year_label] = output_dict[geo_type]
            
    print("calculated land use diversity values sucessfully")


    # ============================write out updated json to file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"VMTReport{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(json_loaded, f_out, indent=4)

    arcpy.SetParameterAsText(2, out_file)
        
    arcpy.AddMessage(f"wrote JSON output to {out_file}")


