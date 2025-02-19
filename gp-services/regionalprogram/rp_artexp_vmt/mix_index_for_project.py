# Esri start of added variables
# g_ESRI_variable_1 = 'fl_parcel'
g_ESRI_variable_2 = 'fl_project'
# Esri end of added variables

#--------------------------------
# Name:calc_mix_index_sacog.py
# Purpose: calculate the mix index for PPA, with emphasis on measuring how
#          conducive the land use mix is to replacing drive trips with walk
   #        trips due to daily needs like retail, schools, etc. being within walk 
#            or short drive distance. Default is based on 1mi buffer around project.        

# Author: Darren Conly
# Last Updated: 11/2019
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
from pathlib import Path
import sys
sys.path.append(Path(__file__).parent.parent) # enable importing from parent folder

from time import perf_counter as perf
import pandas as pd
import arcpy

import parameters as params
from utils import utils

# =============FUNCTIONS=============================================


def make_summary_df(in_fl, input_cols):

    # load into dataframe
    parcel_df = utils.esri_object_to_df(in_fl, input_cols)

    out_df = pd.DataFrame(parcel_df[input_cols].sum(axis = 0)).T

    return out_df


def get_wtd_idx(x, facs, params_df):
    output = 0
    
    for fac in facs:
        fac_ratio = '{}_ratio'.format(fac)
        fac_out = x[fac_ratio] * params_df.loc[fac]['weight']
        output += fac_out
    
    return output
        

def calc_mix_index(in_df, params_df, hh_col, mix_idx_col):
    lu_facs = params_df.index

    # set up for penalty factor for very low density areas.
    area_ac = in_df[params.col_area_ac].values[0]
    dens = (in_df[hh_col].sum() + in_df[params.col_emptot].sum()) / area_ac

    dens_cutoff = 0.5 # if fewer than this many jobs + hh per acre, start penalizing mix score for being in too low-density area
    penaltyfac = min(1, dens / dens_cutoff) # 1 = no penalty
    
    # do mix index calc
    for fac in lu_facs:
        
        # add column for the "ideal", or "balanced" ratio of that land use to HHs
        bal_col = "{}_bal".format(fac) 
        in_df.loc[in_df[hh_col] != 0, bal_col] = in_df[hh_col] * params_df.loc[fac]['bal_ratio_per_hh']
        
        # if no HH, set bal_col = -1
        in_df.fillna(-1)
        
        ratio_col = "{}_ratio".format(fac)
        in_df[ratio_col] = in_df.apply(lambda x: min(x[bal_col], x[fac]) / max(x[bal_col], x[fac]), axis=1)
        
        # if no HH, set ratio col = -1
        in_df.fillna(-1)
        
    in_df[mix_idx_col] = in_df.apply(lambda x: get_wtd_idx(x, lu_facs, params_df), axis=1)
    in_df[mix_idx_col] = in_df[mix_idx_col] * penaltyfac # apply penalty factor for very low density areas (that may have "good" mix)
    
    return in_df


def get_mix_idx(fc_parcel, fc_project, project_type, buffered_pcls=False):
    arcpy.AddMessage("Calculating mix index...")

    params_csv = Path(params.config_csvs_dir).joinpath('mix_idx_params.csv')
    mix_idx_params = pd.read_csv(params_csv, index_col='lu_fac')

    sufx = int(perf()) + 1
    fl_parcel = str(Path(arcpy.env.scratchGDB).joinpath(f'fl_parcel{sufx}'))
    fl_project = g_ESRI_variable_2

    if arcpy.Exists(fl_parcel): arcpy.Delete_management(fl_parcel)
    arcpy.MakeFeatureLayer_management(fc_parcel, fl_parcel)
    
    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)

    in_cols = [params.col_parcelid, params.col_hh, params.col_k12_enr, params.col_emptot, params.col_empfood,
               params.col_empret, params.col_empsvc, params.col_area_ac, params.col_lutype]
    
    # make parcel feature layer
    if not buffered_pcls:
        buffer_dist = 0 if project_type == params.ptype_area_agg else params.mix_index_buffdist
        arcpy.SelectLayerByLocation_management(fl_parcel, "WITHIN_A_DISTANCE", fl_project, buffer_dist, "NEW_SELECTION")

    summ_df = make_summary_df(fl_parcel, in_cols)

    out_df = calc_mix_index(summ_df, mix_idx_params, params.col_hh, params.mix_idx_col)

    out_val = out_df[params.mix_idx_col][0]
    return {params.mix_idx_col: out_val}

# ===============================SCRIPT=================================================

if __name__ == '__main__':
    
    arcpy.env.workspace = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb'
    # input line project for basing spatial selection
    project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Broadway16th_2226'
    buff_dist_ft = params.mix_index_buffdist  # distance in feet--MIGHT NEED TO BE ADJUSTED FOR WGS 84--SEE OLD TOOL FOR HOW THIS WAS RESOLVED
    data_years = [params.base_year, params.future_year]

    out_dict = {}
    for data_year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(in_year=data_year) # input fc of parcel data--must be points!
        year_dict = get_mix_idx(in_pcl_pt_fc, project_fc, params.ptype_arterial)
        out_dict[data_year] = year_dict

    print(out_dict)
    


