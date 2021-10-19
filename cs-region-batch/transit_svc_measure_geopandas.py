# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_projline'
g_ESRI_variable_2 = 'fl_trnstp'
g_ESRI_variable_3 = 'fl_buff'
# Esri end of added variables

# --------------------------------
# Name: transit_svc_measure.py
# Purpose: Estimate transit service density near project
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import gc
import time

import csi_params as params


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


def get_poly_area(poly_geom):
    buff_area_ft2 = poly_geom.area
    buff_acre = buff_area_ft2 / params.ft2acre  # convert from ft2 to acres. may need to adjust for projection-related issues. See PPA1 for more info
    return buff_acre

def transit_svc_density(gdf_project, gdf_trnstops, project_type):

    # arcpy.AddMessage("calculating transit service density...")

    try:
        
        # analysis area. If project is line or point, then it's a buffer around the line/point.
        # If it's a polygon (e.g. ctype or region), then no buffer and analysis area is that within the input polygon
        if project_type == params.ptype_area_agg:
            geom_buff = gdf_project
        else:
            geom_buff = gdf_project.buffer(params.trn_buff_dist).unary_union

        # calculate buffer area
        buff_acres = get_poly_area(geom_buff)

        # get count of transit stops within buffer
        gdf_selected_stopevs = gdf_trnstops.loc[gdf_trnstops.geometry.within(geom_buff) == True]
        transit_veh_events = gdf_selected_stopevs.shape[0]

        trnstops_per_acre = transit_veh_events / buff_acres if buff_acres > 0 else 0

    except:
        trnstops_per_acre = -1.0 
        msg = "{}, {}".format(arcpy.GetMessages(2), trace())
        arcpy.AddWarning(msg)
    finally:
        return {"TrnVehStop_Acre": trnstops_per_acre}
        n = gc.collect()




        
'''
if __name__ == '__main__':
    arcpy.env.workspace = None

    proj_line_fc = None
    trnstops_fc = 'transit_stoplocn_w_eventcount_2016'
    ptype = params.ptype_arterial

    output = transit_svc_density(proj_line_fc, trnstops_fc, ptype)
    print(output)
'''
