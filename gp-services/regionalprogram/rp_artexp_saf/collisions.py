# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# --------------------------------
# Name:collisions.py
# Purpose: calculate collision data for PPA tool based on geocoded TIMS data (tims.berkeley.edu)
# notably, this version, when computing total collisions and centerline miles within polygon,
# will exclude centerline miles and collisions from local streets. This is because there are many
# miles of local streets, and including can deflate collision rate per centerline mile to such a low
# rate that virtually all projects are guaranteed to look good, which doesn't help with prioritizing.
# 
# Author: Darren Conly
# Last Updated: Aug 2022
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
from time import perf_counter as perf

import arcpy
import pandas as pd

from config_links import params
from utils import utils as ut


# for aggregate, polygon-based avgs (e.g., community type, whole region), use model for VMT; for
# project, the VMT will be based on combo of project length and user-entered ADT for project
def get_model_link_sums(fc_polygon, fc_model_links):
    '''For all travel model highway links that have their center within a polygon (e.g. buffer
    around a project line, or a community type, or a trip shed), sum the values for user-specified
    metrics. E.g. daily VMT for all selected intersectin model links, total lane miles on intersecting
    links, etc.'''

    fl_polygon = 'fl_polygon'
    fl_model_links = 'fl_model_links'
    
    if arcpy.Exists(fl_polygon): arcpy.Delete_management(fl_polygon)
    arcpy.MakeFeatureLayer_management(fc_polygon, fl_polygon)
    
    if arcpy.Exists(fl_model_links): arcpy.Delete_management(fl_model_links)
    arcpy.MakeFeatureLayer_management(fc_model_links, fl_model_links)

    # select model links whose centroid is within the polygon area
    arcpy.SelectLayerByLocation_management(fl_model_links, "HAVE_THEIR_CENTER_IN", fl_polygon)

    link_data_cols =[params.col_capclass, params.col_distance, params.col_lanemi, params.col_dayvmt]
    output_data_cols =[params.col_dayvmt, params.col_distance]

    # load model links, selected to be near project, into a dataframe
    df_linkdata = ut.esri_object_to_df(fl_model_links, link_data_cols)

    # add simple 0/1 freeway tag
    df_linkdata['fwy_yn'] = 0
    df_linkdata.loc[df_linkdata[params.col_capclass].isin(params.capclasses_fwy), 'fwy_yn'] = 1

    # get appropriate totals for freeways and non-freeways
    df_linksums = df_linkdata.groupby('fwy_yn')[output_data_cols].sum()

    out_dict = df_linksums.to_dict(orient='index')


    # get total VMT for links within the area
    # out_dict = {col: df_linkdata[col].sum() for col in output_data_cols}
    return out_dict


def get_centerline_miles(selection_poly_fc, centerline_fc):
    '''Calculate centerline miles for all road links whose center is within a polygon,
    such as a buffer around a road segment, or community type, trip shed, etc.'''

    fl_selection_poly = 'fl_selection_poly'
    fl_centerline = 'fl_centerline'
    
    if arcpy.Exists(fl_selection_poly): arcpy.Delete_management(fl_selection_poly)
    arcpy.MakeFeatureLayer_management(selection_poly_fc, fl_selection_poly)
    
    if arcpy.Exists(fl_centerline): arcpy.Delete_management(fl_centerline)
    arcpy.MakeFeatureLayer_management(centerline_fc, fl_centerline)

    arcpy.SelectLayerByLocation_management(fl_centerline, "HAVE_THEIR_CENTER_IN", fl_selection_poly)

    cline_miles = 0
    with arcpy.da.SearchCursor(fl_centerline, "SHAPE@LENGTH") as cur:
        for row in cur:
            cline_miles += row[0]

    return cline_miles / params.ft2mile

def final_agg(in_df, ann_vmt, proj_len_mi, factyp_tag):
    total_collns = in_df.shape[0]
    fatal_collns = in_df.loc[in_df[params.col_nkilled] > 0].shape[0]
    bikeped_collns = in_df.loc[(in_df[params.col_bike_ind] == params.ind_val_true)
                                      | (in_df[params.col_ped_ind] == params.ind_val_true)].shape[0]
    pct_bikeped_collns = bikeped_collns / total_collns if total_collns > 0 else 0

    bikeped_colln_clmile = bikeped_collns / proj_len_mi

    # collisions per million VMT (MVMT) = avg annual collisions / (modeled daily VMT * 320 days) * 1,000,000
    avg_ann_collisions = total_collns / params.years_of_collndata
    avg_ann_fatalcolln = fatal_collns / params.years_of_collndata

    colln_rate_per_vmt = avg_ann_collisions / ann_vmt * 100000000 if ann_vmt > 0 else -1
    fatalcolln_per_vmt = avg_ann_fatalcolln / ann_vmt * 100000000 if ann_vmt > 0 else -1
    pct_fatal_collns = avg_ann_fatalcolln / avg_ann_collisions if avg_ann_collisions > 0 else 0

    out_dict = {f"TOT_COLLISNS": total_collns, f"TOT_COLLISNS_PER_100MVMT": colln_rate_per_vmt,
                f"FATAL_COLLISNS": fatal_collns, f"FATAL_COLLISNS_PER_100MVMT": fatalcolln_per_vmt,
                f"PCT_FATAL_COLLISNS": pct_fatal_collns, f"BIKEPED_COLLISNS": bikeped_collns, 
                f"BIKEPED_COLLISNS_PER_CLMILE": bikeped_colln_clmile, f"PCT_BIKEPED_COLLISNS": pct_bikeped_collns}
    
    out_dict_roadtyp_tag = {f"{k}{factyp_tag}":v for k, v in out_dict.items()}

    output_df = pd.DataFrame(pd.Series(out_dict, index=list(out_dict.keys()))).reset_index()
    output_df[params.col_fwytag] = factyp_tag

    return out_dict_roadtyp_tag

def get_collision_data(fc_project, project_type, fc_colln_pts, project_adt):
    '''Inputs:
        fc_project = project line around which a buffer will be drawn for selecting collision locations
        project_type = whether it's a freeway project, arterial project, etc. Or if it is a 
        community design project.
        
        With user-entered ADT (avg daily traffic) and a point layer of collision locations, function calculates
        several key safety metrics including total collisions, collisions/100M VMT, percent bike/ped collisions, etc.'''
        
    arcpy.AddMessage("Aggregating collision data...")

    fc_model_links = params.model_links_fc()

    fl_project = 'proj_fl'
    fl_colln_pts = 'fl_colln_pts'
    
    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)
    
    if arcpy.Exists(fl_colln_pts): arcpy.Delete_management(fl_colln_pts)
    arcpy.MakeFeatureLayer_management(fc_colln_pts, fl_colln_pts)

    # if for project segment, get annual VMT for project segment based on user input and segment length
    f_shplen = "SHAPE@LENGTH"
    df_projlen = ut.esri_object_to_df(fl_project, [f_shplen])
    proj_len_mi = df_projlen[f_shplen].sum() / params.ft2mile  # return project length in miles

    # for aggregate, polygon-based avgs (e.g., community type, whole region), use model for VMT; for
    # project, the VMT will be based on combo of project length and user-entered ADT for project
    # approximate annual project VMT, assuming ADT is reflective of weekdays only, but assumes
    if project_type == params.ptype_area_agg:
        vmt_dict = get_model_link_sums(fc_project, fc_model_links)
        ann_vmt_fwy = vmt_dict[1][params.col_dayvmt] * params.ann_factor
        ann_vmt_nonfwy = vmt_dict[0][params.col_dayvmt] * params.ann_factor
        proj_len_mi = get_centerline_miles(fc_project, params.reg_artcollcline_fc) # only gets for collector streets and above
    else:
        ann_proj_vmt = project_adt * proj_len_mi * params.ann_factor


    # get collision totals, separate tables for each facility tpe
    searchdist = 0 if project_type == params.ptype_area_agg else params.colln_searchdist
    arcpy.SelectLayerByLocation_management(fl_colln_pts, 'WITHIN_A_DISTANCE', fl_project, searchdist)
    colln_cols =[params.col_fwytag, params.col_nkilled, params.col_bike_ind, params.col_ped_ind]
    
    df_collndata = ut.esri_object_to_df(fl_colln_pts, colln_cols)
    df_collndata_fwy = df_collndata.loc[df_collndata[params.col_fwytag] == params.ind_fwytag_fwy]
    df_collndata_nonfwy = df_collndata.loc[df_collndata[params.col_fwytag] != params.ind_fwytag_fwy]

    if project_type == params.ptype_area_agg:
        tag_fwy = params.tags_ptypes[params.ptypes_fwy[0]]
        tag_nonfwy = params.tags_ptypes[params.ptype_arterial]
        out_dict = final_agg(df_collndata_fwy, ann_vmt_fwy, proj_len_mi, tag_fwy)
        odict_nonfwy = final_agg(df_collndata_nonfwy, ann_vmt_nonfwy, proj_len_mi, tag_nonfwy)

        out_dict.update(odict_nonfwy)
        # out_dict = odict_fwy.update(odict_nonfwy)
    elif project_type in params.ptypes_fwy:
        out_dict = final_agg(df_collndata_fwy, ann_proj_vmt, proj_len_mi, "")
    else:
        out_dict = final_agg(df_collndata_nonfwy, ann_proj_vmt, proj_len_mi, "")

    return out_dict
