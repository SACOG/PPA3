# --------------------------------
# Name: accessibility_calcs.py
# Purpose: PPA accessibility metrics using Sugar-access polygons (default is census block groups)
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from time import perf_counter as perf

import pandas as pd
import arcpy
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask

import parameters as params
from utils import utils as ut


def get_raster_pts_near_line(tif, line_fc, mode, dest_type):

    # load tif data
    with rasterio.open(tif) as tifdata:
        epsg_id = tifdata.crs.to_epsg()
        crs_linunits = tifdata.crs.linear_units # placeholder in case you ever want to know what units the CRS uses.
        crs_to_use = f"EPSG:{epsg_id}"
        vals_masked, valmasked_transform = mask(tifdata, shapes=[mask_geom], all_touched=True, 
                                                crop=True, pad=True, pad_width=0.5)
        vals_array = vals_masked[0]

    # create buffered line object around project line
    line_gdf = ut.esri_to_df(esri_obj_path=line_fc, include_geom=True, field_list=None, index_field=None, 
                   crs_val=crs_to_use, dissolve=False)
    line_gdf['geometry'] = line_gdf['geometry'].buffer(100) # distance in meters if EPSG 3857 (web mercator)

    mask_geom = line_gdf.geometry[0]

    # make vector point gdf from the pixels that are near the line. Will need to further trim to go from
    # rectangle of points to just points that are right along the line.
    # helpful site = https://gis.stackexchange.com/questions/388047/get-coordinates-of-all-pixels-in-a-raster-with-rasterio
    row_range = np.arange(vals_array.shape[0])
    col_range = np.arange(vals_array.shape[1])

    coord_arr = []
    valname = f"{mode}_{dest_type}"
    for r in row_range:
        for c in col_range:
            x, y = rasterio.transform.xy(valmasked_transform, r, c)
            val = vals_array[r][c]
            coord_arr.append({'cellid': f"{r}_{c}", 'x': x, 'y': y, valname: val})

    df = pd.DataFrame(coord_arr)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y), crs=crs_to_use)
    
    return gdf


def get_acc_data(fc_project, tif_accdata, tif_weights, project_type, get_ej=False):
    '''Calculate average accessibility to selected destination types for all
    polygons that either intersect the project line or are within a community type polygon.
    Average accessibility is weighted by each polygon's population.'''
    
    arcpy.AddMessage("Calculating accessibility metrics...")

    # load tifs and trim to those near project line
    gdf_acc = get_raster_pts_near_line(tif_accdata, fc_project, mode=, dest_type=)
    gdf_wt = get_raster_pts_near_line(tif_weights, fc_project, mode=, dest_type=)

    # get pop-weighted accessibility values for all accessibility columns
    gdf_jn = 


    # 7/3/2024 - WILL YOU WANT TO GET "ACCESS FOR EJ POPULATIONS" METRIC? IDEALLY COULD REMOVE IT; DOES NOT REALLY TELL US ANYTHING USEFUL.

    out_dict = {}
    if get_ej: # if for enviro justice population, weight by population for EJ polygons only.
        for col in params.acc_cols_ej:
            col_wtd = "{}_wtd".format(col)
            col_ej_pop = "{}_EJ".format(params.col_pop)
            accdata_df[col_wtd] = accdata_df[col] * accdata_df[params.col_pop] * accdata_df[params.col_acc_ej_ind]
            accdata_df[col_ej_pop] = accdata_df[params.col_pop] * accdata_df[params.col_acc_ej_ind]
            
            tot_ej_pop = accdata_df[col_ej_pop].sum()
            
            out_wtd_acc = accdata_df[col_wtd].sum() / tot_ej_pop if tot_ej_pop > 0 else 0
            col_out_ej = "{}_EJ".format(col)
            out_dict[col_out_ej] = out_wtd_acc
    else:
        total_pop = accdata_df[params.col_pop].sum()
        for col in params.acc_cols:
            if total_pop <= 0: # if no one lives near project, get unweighted avg accessibility of block groups near project
                out_wtd_acc = accdata_df[col].mean()
            else:
                col_wtd = "{}_wtd".format(col)
                accdata_df[col_wtd] = accdata_df[col] * accdata_df[params.col_pop]
                out_wtd_acc = accdata_df[col_wtd].sum() / total_pop
                
            out_dict[col] = out_wtd_acc

    return out_dict


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
    
    fc_project_line = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Polylines'
    fc_accessibility_data = params.accdata_fc
    str_project_type = params.ptype_arterial
    
    dict_data = get_acc_data(fc_project_line, fc_accessibility_data, str_project_type)
    arcpy.AddMessage(dict_data)
    
