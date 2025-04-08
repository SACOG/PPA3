# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'proj_fl'
g_ESRI_variable_2 = 'modlink_fl'
# Esri end of added variables

# --------------------------------
# Name: link_occup_data.py
# Purpose: compute transit trip vol and vehicle occup on project based on SACSIM mode links
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import math

import arcpy

from config_links import params
from utils import utils as ut

def link_vehocc(row):
    vol_sov = row[params.col_sovvol]
    vol_hov2 = row[params.col_hov2vol]
    vol_hov3 = row[params.col_hov3vol]
    vol_commveh = row[params.col_daycommvehvol]
    total_veh_vol = sum([vol_sov, vol_hov2, vol_hov3, vol_commveh])

    # 12/19/22 old method: comput average vehicle occupancy
    # out_row = (vol_commveh + vol_sov + vol_hov2 * params.fac_hov2 + vol_hov3 * params.fac_hov3) / total_veh_vol

    # 12/19/22 - new method, compute total people in all vehs, rather than avg veh occupancy
    out_row = (vol_commveh + vol_sov + vol_hov2 * params.fac_hov2 + vol_hov3 * params.fac_hov3)
    return out_row

def get_angle(in_line_geom):
    """Takes in ESRI line geometry object and retrieves its angle.
    Meant to be used within search or update cursors"""
    start_lat = in_line_geom.firstPoint.Y
    start_lon = in_line_geom.firstPoint.X
    end_lat = in_line_geom.lastPoint.Y
    end_lon = in_line_geom.lastPoint.X
    
    xdiff = end_lon - start_lon
    ydiff = end_lat - start_lat
    link_angle = math.degrees(math.atan2(ydiff, xdiff))
    return link_angle

def get_wtdavg_vehocc(in_df):

    # col_wtdvol = 'col_wtdvol'
    col_persncnt = 'persncnt'
    col_ppv = 'person_perveh'

    in_df = in_df.loc[in_df[params.col_dayvehvol] > 0]  # exclude links with daily volume of zero.
    in_df[col_persncnt] = in_df.apply(lambda x: link_vehocc(x), axis = 1)
    in_df[col_ppv] = in_df[col_persncnt] / in_df[params.col_dayvehvol]

    # new method: avg vehicle occupancy weighted by traffic vol on all links
    output_val = (in_df[col_ppv] * in_df[params.col_dayvehvol]).sum() / in_df[params.col_dayvehvol].sum()

    return output_val


def trantrp_per_link(in_df, project_type):
    # compute average # of transit trips per road link

    in_df_ptyp = in_df
    if project_type == params.ptype_fwy:
        # if project is fwy project, then only use GP links; adding HOV or aux links may
        # make it appear as if decrease in transit trips because % change in links may exceed % change in transit trips
        in_df_ptyp = in_df.loc[in_df[params.col_capclass] == params.capclass_gp]

    link_cnt = in_df_ptyp.shape[0]
    tot_trntrip = in_df[params.col_tranvol].sum() # want transit trips on all link types

    # if freeway, is (total transit trips on all fwy link types) / (# of GP fwy links)
    return tot_trntrip / link_cnt


def get_linkoccup_data(fc_project, project_type, fc_model_links):
    arcpy.AddMessage("Getting modeled vehicle occupancy data...")
    fl_project = g_ESRI_variable_1
    fl_model_links = g_ESRI_variable_2

    angle_tolerance = 15 # if angle diff between road link and project link exceeds this, then is not candidate for conflation
    f_oid = 'OBJECTID'

    if arcpy.Exists(fl_project): arcpy.management.Delete(fl_project)
    if arcpy.Exists(fl_model_links): arcpy.management.Delete(fl_model_links)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)
    arcpy.MakeFeatureLayer_management(fc_model_links, fl_model_links)

    # get model links that are on specified link type within search distance of project
    # arcpy.SelectLayerByLocation_management(fl_model_links, 'HAVE_THEIR_CENTER_IN', fl_project, params.modlink_searchdist)
    arcpy.SelectLayerByLocation_management(fl_model_links, 'WITHIN_A_DISTANCE', fl_project, params.modlink_searchdist)
    
    # get list of angles of project piece(s)
    proj_geoms = []
    with arcpy.da.SearchCursor(fl_project, field_names=['SHAPE@']) as scur:
        for row in scur: proj_geoms.append(row[0])

    # for each project piece, from nearby model links, get IDs for links that are aligned (either same dir or direct opposite dir) of project line.
    aligned_links = []
    for pg in proj_geoms:
        ang_pg = get_angle(pg)
        with arcpy.da.SearchCursor(fl_model_links, field_names=['SHAPE@', f_oid]) as scur:
            for row in scur:
                ang = get_angle(row[0])
                ang_v_proj = abs(ang_pg) - abs(ang)
                if ang_v_proj < angle_tolerance:
                    aligned_links.append(row[1])

    # load data into dataframe then subselect only ones that are on same road type as project (e.g. fwy vs. arterial)
    df_cols = [f_oid, params.col_capclass, params.col_distance, params.col_lanemi, params.col_tranvol, params.col_dayvehvol, params.col_sovvol,  
               params.col_hov2vol, params.col_hov3vol, params.col_daycommvehvol]
    df_linkdata = ut.esri_object_to_df(fl_model_links, df_cols)
    df_linkdata = df_linkdata[df_linkdata[f_oid].isin(aligned_links)]

    if project_type == params.ptype_fwy:
        df_linkdata = df_linkdata.loc[df_linkdata[params.col_capclass].isin(params.capclasses_fwy)]
    else:
        df_linkdata = df_linkdata.loc[df_linkdata[params.col_capclass].isin(params.capclass_arterials)]

    df_linkdata = df_linkdata.fillna(0)
    
    avg_proj_trantrips = trantrp_per_link(df_linkdata, project_type) if df_linkdata.shape[0] > 0 else 0
    avg_proj_vehocc = get_wtdavg_vehocc(df_linkdata) if df_linkdata.shape[0] > 0 else 0

    out_dict = {"avg_2way_trantrips": avg_proj_trantrips, "avg_2way_vehocc": avg_proj_vehocc}

    return out_dict


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    proj_line_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_I5SMF'
    model_link_fc = 'model_links_2040'
    proj_type = params.ptype_fwy

    output = get_linkoccup_data(proj_line_fc, proj_type, model_link_fc)

    print(output)

