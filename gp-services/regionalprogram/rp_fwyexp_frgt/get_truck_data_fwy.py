# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_project'
g_ESRI_variable_2 = 'fl_speed_data'
g_ESRI_variable_3 = '{} IN {}'
g_ESRI_variable_4 = 'fl_tmc_buff'
# Esri end of added variables

#--------------------------------
# Name:get_truck_data_fwy.py
# Purpose: Estimate share of traffic on freeways that is trucks; based on Caltrans truck counts.
#          
#           
# Author: Darren Conly
# Last Updated: 02/2020
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: <version>
#--------------------------------


import os

import arcpy
import pandas as pd

from config_links import params
import npmrds_data_conflation as ndc

def get_wtdavg_truckdata(in_df, col_name):
    len_cols = ['{}_calc_len'.format(dirn) for dirn in params.directions_tmc]
    val_cols = ['{}{}'.format(dirn, col_name) for dirn in params.directions_tmc]

    usable_cols = list(in_df.columns)
    wtd_dict = dict(zip(len_cols, val_cols))
    wtd_dict = {k: v for k, v in wtd_dict.items() if v in usable_cols}

    wtd_val_sum = 0
    dist_sum = 0

    for dirlen, dirval in wtd_dict.items():
        dir_val2 = 0 if pd.isnull(in_df[dirval][0]) else in_df[dirval][0]
        dir_wtdval = in_df[dirlen][0] * dir_val2
        wtd_val_sum += dir_wtdval
        dist_sum += in_df[dirlen][0]

    return wtd_val_sum / dist_sum if dist_sum > 0 else -1




def get_tmc_truck_data(fc_projline, str_project_type):

    arcpy.OverwriteOutput = True
    fl_projline = g_ESRI_variable_1
    arcpy.MakeFeatureLayer_management(fc_projline, fl_projline)

    # make feature layer from speed data feature class
    fl_speed_data = g_ESRI_variable_2
    arcpy.MakeFeatureLayer_management(params.fc_speed_data, fl_speed_data)

    # make flat-ended buffers around TMCs that intersect project
    arcpy.SelectLayerByLocation_management(fl_speed_data, "WITHIN_A_DISTANCE", fl_projline, params.tmc_select_srchdist, "NEW_SELECTION")
    if str_project_type in params.ptypes_fwy:
        sql = g_ESRI_variable_3.format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)
    else:
        sql = "{} NOT IN {}".format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)

    # create temporar buffer layer, flat-tipped, around TMCs; will be used to split project lines
    scratch_gdb = arcpy.env.scratchGDB
        
    temp_tmcbuff = os.path.join(scratch_gdb, "TEMP_tmcbuff_4projsplit")
    fl_tmc_buff = g_ESRI_variable_4
    arcpy.Buffer_analysis(fl_speed_data, temp_tmcbuff, params.tmc_buff_dist_ft, "FULL", "FLAT")
    arcpy.MakeFeatureLayer_management(temp_tmcbuff, fl_tmc_buff)

    # get "full" table with data for all directions
    # conflate_tmc_to_project(project_layer, directions, tmc_dir_field, buffer_layer, tmc_layer, field_methods)
    fl_speed = "fl_speed_data"
    arcpy.MakeFeatureLayer_management(params.fc_speed_data, fl_speed)
    projdata_df = ndc.conflate_tmc_to_project(fl_projline, params.directions_tmc, params.col_tmcdir, 
                                            fl_tmc_buff, fl_speed, params.truck_data_calc_dict)
    
    arcpy.AddMessage(str(projdata_df))

    out_dict = {}
    for field, calcmthd in params.truck_data_calc_dict.items():
        if calcmthd == params.calc_distwt_avg:
            output_val = get_wtdavg_truckdata(projdata_df, field)
            out_dict["{}_proj".format(field)] = output_val
        else:
            continue
        
    return out_dict

if __name__ == '__main__':

    arcpy.env.workspace = params.fgdb
    arcpy.env.overwriteOutput = True

    project_line = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_Causeway'
    proj_type = params.ptypes_fwy[0]

    # make feature layers of NPMRDS and project line

    output_dict = get_tmc_truck_data(project_line, proj_type)
    print(output_dict)

