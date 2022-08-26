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

def build_bg_df(fc_blk_grp, csvs_bg_data=[]):
    dir_bgs = os.path.dirname(fc_blk_grp)
    name_bgs = os.path.basename(fc_blk_grp)

    f_bg_geoid = 'GEOID'
    f_geom = 'geometry'

    flds_bgs = [f_bg_geoid, f_geom]

    print(f"loading {fc_blk_grp}...")
    gdf_bgs = gpd.read_file(dir_bgs, layer=name_bgs, driver="OpenFileGDB")[flds_bgs]

    dtype_id_gdf = gdf_bgs[f_bg_geoid].dtype
    
    if len(csvs_bg_data) > 0:
        for in_csv in csvs_bg_data:
            df = pd.read_csv(in_csv)
            dtyp_id_csv = df[f_bg_geoid].dtype
            
            if dtyp_id_csv == dtype_id_gdf:
                df_out = gdf_bgs.merge(df, on=f_bg_geoid)
            elif dtype_id_gdf == 'O':
                gdf_bgs[f_bg_geoid] = gdf_bgs[f_bg_geoid].astype(dtyp_id_csv)
                df_out = gdf_bgs.merge(df, on=f_bg_geoid)
            else:
                raise Exception(f"Join failed due to mismatched data types. {in_csv} has {f_bg_geoid} dtype of {dtyp_id_csv}, " \
                    f"while bg geodatframe {f_bg_geoid} field has dtype of {dtype_id_gdf}")
    else:
        df_out = gdf_bgs

    return df_out
        

def initial_sjoin(fc_pcl_pts, gdf_bgs):

    dir_pcls = os.path.dirname(fc_pcl_pts)
    name_pcls = os.path.basename(fc_pcl_pts)



    # field names
    f_pcl_id = 'PARCELID'
    f_pcl_du = 'DU_TOT'
    f_geom = 'geometry' 

    flds_pclpts = [f_pcl_id, f_pcl_du, f_geom]

    # load parcel to geodataframe
    print(f"loading {fc_pcl_pts}...")
    gdf_parcels = gpd.read_file(dir_pcls, layer=name_pcls, driver="OpenFileGDB")[flds_pclpts]

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
    f_bg_geoid = 'GEOID'
    f_du_tot = 'DU_TOT'
    flds_pclpolys = [f_parcelid, f_geom]

    # load polyong parcel data
    print(f"loading {fc_pcl_polys}...")
    gdf_pclpolys = gpd.read_file(dir_pclpolys, layer=name_pclpolys, driver="OpenFileGDB")[flds_pclpolys]

    del in_gdf[f_geom], in_gdf[f_du_tot]

    # join point parcel data (with block group ID) to polygon parcel data via parcelid attribute
    print(f"joining parcel point data to parcel poly layer via {f_parcelid}")
    gdf_jn = in_gdf.merge(gdf_pclpolys, how='inner', on=f_parcelid)

    # dissolve parcels by block group ID
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
    pclpts = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\parcel_data_pts_2016'
    # pclpts = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\parcel_data_pt_sample'

    pclpolys = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\parcel_data_polys_2016'
    # pclpolys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\parcel_data_polys_sample'
    

    bg_polys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\Census_BlockGroups2020_region'
    bg_data_csv = r"I:\Projects\Darren\PPA3_GIS\CSV\Census2020\BGRaceDataCensus2020.csv"
    bg_data_desc = 'RaceEth'
    bg_year = 2020

    output_dir = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb'

    # ============RUN SCRIPT==================

    time_sufx = strftime(dt.now(), "%Y%M%d_%H%M")
    out_fc_name = f"blockgrp_{bg_data_desc}{bg_year}_{time_sufx}"
    out_fc_path = os.path.join(output_dir, out_fc_name)

    df_bgs = build_bg_df(bg_polys, csvs_bg_data=[bg_data_csv])
    df_1 = initial_sjoin(pclpts, df_bgs)
    make_final_output_file(df_1, pclpolys, out_fc_path)
