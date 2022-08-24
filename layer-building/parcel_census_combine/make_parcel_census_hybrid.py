"""
Name: make_parcel_census_hybrid.py
Purpose: 
    Demographic data for race and poverty come from census block groups, 
    but a project’s vicinity buffer will generally intersect pieces of each block group. 
    Typical practice is to assume that a block group’s population is evenly spread throughout the block group. 
    However, this is often wrong because people frequently live in just one part of the block group. 
    To overcome this issue, we did the following:

    1.	Filter parcel point file to only keep parcels where there was at least one dwelling unit on the parcel.
    2.	Spatial join resulting parcel points to block groups, tagging a block group ID onto each parcel point.
    3.	Attribute join the parcel point layer to a parcel polygon layer based on parcel ID. 
    4.	Dissolve parcel polygon layer by block group ID, leaving a single polygon for each census geography, but whose geometry would only include parcels with dwelling units.

Author: Darren Conly
Last Updated: Aug 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""


import os
from datetime import datetime as dt
from time import perf_counter

# import arcpy
from arcgis.features import GeoAccessor, GeoSeriesAccessor

import geopandas as gpd
from isodate import strftime
import pandas as pd


def initial_sjoin(fc_pcl_pts, fc_blk_grp, bg_data_fields=[]):

    dir_pcls = os.path.dirname(fc_pcl_pts)
    name_pcls = os.path.basename(fc_pcl_pts)

    dir_bgs = os.path.dirname(fc_blk_grp)
    name_bgs = os.path.basename(fc_blk_grp)

    # field names
    f_pcl_id = 'PARCELID'
    f_pcl_du = 'DU_TOT'
    f_bg_geoid = 'GEOID10'
    f_geom = 'geometry' 

    flds_pclpts = [f_pcl_id, f_pcl_du, f_geom]
    flds_bgs = [f_bg_geoid, f_geom] + bg_data_fields

    # load parcel to geodataframe
    print(f"loading {fc_pcl_pts}...")
    gdf_parcels = gpd.read_file(dir_pcls, layer=name_pcls, driver="OpenFileGDB")[flds_pclpts]

    print(f"loading {fc_blk_grp}...")
    gdf_bgs = gpd.read_file(dir_bgs, layer=name_bgs, driver="OpenFileGDB")[flds_bgs]

    # spatial join filtered parcel points with block groups, to get block group ID tagged to each parcel point
    print(f"spatial joining...")
    gdf_parcels = gdf_parcels.loc[gdf_parcels[f_pcl_du] > 0] # only want inhabited parcels
    gdf_pcls_w_bgid = gpd.sjoin(gdf_parcels, gdf_bgs, how='left', op='intersects')

    return gdf_pcls_w_bgid

def make_final_output_file(in_gdf, fc_pcl_polys, output_fc):

    dir_pclpolys = os.path.dirname(fc_pcl_polys)
    name_pclpolys = os.path.basename(fc_pcl_polys)

    f_geom = "geometry"
    f_parcelid = 'PARCELID'
    f_bg_geoid = 'GEOID10'
    flds_pclpolys = [f_parcelid, f_geom]

    # load polyong parcel data
    print(f"loading {fc_pcl_polys}...")
    gdf_pclpolys = gpd.read_file(dir_pclpolys, layer=name_pclpolys, driver="OpenFileGDB")[flds_pclpolys]

    del in_gdf[f_geom]

    # join point parcel data (with block group ID) to polygon parcel data via parcelid attribute
    print(f"joining parcel point data to parcel poly layer via {f_parcelid}")
    gdf_jn = in_gdf.merge(gdf_pclpolys, how='inner', on=f_parcelid)


    # dissolve parcels by 
    print(f"dissolving by {f_bg_geoid}...")
    gdf_out = gdf_jn.dissolve(by=f_bg_geoid, aggfunc='mean')

    # free up some memory
    del gdf_jn

    # convert to esri sedf to enable export to esri feature class
    print(f"exporting to {output_fc}")
    sedf_out = pd.DataFrame.spatial.from_geodataframe(gdf_out)
    sedf_out.spatial.to_featureclass(output_fc)
    print("success!")

    

if __name__ == '__main__':
    # pclpts = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\parcel_data_pts_2016'
    pclpts = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\parcel_data_pt_sample'

    # pclpolys = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\parcel_data_polys_2016'
    pclpolys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\parcel_data_polys_sample'
    

    bg_polys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\Census_BlockGroups2010_region'
    bg_year = 2010

    # bg_polys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\Census_BlockGroups2020_region'
    # bg_year = 2020

    output_dir = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb'

    # ============RUN SCRIPT==================

    time_sufx = strftime(dt.now(), "%Y%M%d_%H%M")
    out_fc_name = f"blockgrp_areaswppl{bg_year}_{time_sufx}"
    out_fc_path = os.path.join(output_dir, out_fc_name)

    df_1 = initial_sjoin(pclpts, bg_polys)
    make_final_output_file(df_1, pclpolys, out_fc_path)
