# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports


# --------------------------------
# Name:get_buff_netmiles.py
# Purpose: get total network and bikeway miles within specified buffer of project, get % of those that are bikeways
#
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------

import arcpy

import parameters as params


def netmiles_in_buffer(fc_project, fc_network, project_type):

    # if project is polygon, then use polygon. If line or point, then make polygon as buffer around line/point.
    if project_type == params.ptype_area_agg:
        fc_poly_buff = fc_project
    else:
        fc_poly_buff = os.path.join('memory', 'temp_buff_qmi')
        arcpy.Buffer_analysis(fc_project, fc_poly_buff, params.bikeway_buff)

    fl_poly = 'fl_buff'

    if arcpy.Exists(fl_poly): arcpy.Delete_management(fl_poly)
    arcpy.MakeFeatureLayer_management(fc_poly_buff, fl_poly)    

    temp_intersect_fc = os.path.join('memory', 'temp_intersect_fc')

    #run intersect of network lines against buffer
    arcpy.Intersect_analysis([fc_network, fc_poly_buff], temp_intersect_fc)

    # get total mileage of network lines-buffer intersection fc
    net_len = 0
    with arcpy.da.SearchCursor(temp_intersect_fc, "SHAPE@LENGTH") as cur:
        for row in cur:
            net_len += row[0]

    arcpy.Delete_management(temp_intersect_fc)

    if fc_poly_buff != fc_project:
        arcpy.Delete_management(fc_poly_buff)
    return net_len


def get_bikeway_mileage_share(project_fc, proj_type):
    # arcpy.AddMessage("Calculating share of centerline miles near project that are bikeways...")

    c_line_layer = os.path.join(params.fgdb, params.reg_centerline_fc)
    bikewy_layer = os.path.join(params.fgdb, params.reg_bikeway_fc)
    centerline_miles = netmiles_in_buffer(project_fc, c_line_layer, proj_type)
    bikeway_miles = netmiles_in_buffer(project_fc, bikewy_layer, proj_type)

    share_bikeways = bikeway_miles / centerline_miles if centerline_miles > 0 else 0

    return {"pct_roadmi_bikeways": share_bikeways}


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    project = 'PPAClientRun_StocktonBlCS'

    test_dict = get_bikeway_mileage_share(project, params.ptype_arterial)

    print(test_dict)

