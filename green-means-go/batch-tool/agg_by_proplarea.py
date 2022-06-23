# -*- coding: utf-8 -*-
#--------------------------------
# Name:agg_by_proplarea.py
# Purpose: if multiple polygons from an "intersect" layer overlap a "target" layer,
#           compute the area-pro-rated value of each "intersect" polygon based on how much
#           it overlaps with the "target" polygon layer
#           
# Author: Darren Conly
# Last Updated: 5/24/2019
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
#--------------------------------

import time
import datetime as dt
import arcpy

arcpy.env.overwriteOutput = True

#==============================

#divide "target" polygons at "intersect" polygon boundaries
def get_areapropl_values(target_fc, intersect_fc, fields_to_compute, output_fc): #clean up, fc_intersect doesn't need to be argument; is temp layer
    # you have multiple intersect_fc polys intersecting one target_fc poly, and you want to get the area of the original intersect_fc poly.

    fld_orig_intsct_area = "AREA_origl" # original area of intersect polygons before doing the intersection
    fld_current_area = "SHAPE@AREA" # current area of polygon

    #add field with intersecting polys' total area
    # print("Intersecting {} with {}...".format(intersect_fc, target_fc))
    # import pdb; pdb.set_trace()
    if fld_orig_intsct_area not in [f.name for f in arcpy.ListFields(intersect_fc)]:
        arcpy.AddField_management(intersect_fc, fld_orig_intsct_area, "FLOAT")

    fields = [fld_orig_intsct_area, fld_current_area]
    with arcpy.da.UpdateCursor(intersect_fc, fields) as cur:
        for row in cur:
            row[fields.index(fld_orig_intsct_area)] = row[fields.index(fld_current_area)]
            cur.updateRow(row)
    
    #do intersection; output will have both intersecting polygons' original area and updated area (reflective of intersection)
    in_features = [intersect_fc, target_fc]
    arcpy.Intersect_analysis(in_features, output_fc)

    # recompute all value fields to reflect updated, area-prorated values.
    # import pdb; pdb.set_trace()
    for f in fields_to_compute:
        # print(f"Recomputing for area-proportional values for {f}...")
        fields_to_use = [fld_orig_intsct_area, fld_current_area, f]
        with arcpy.da.UpdateCursor(output_fc, fields_to_use) as cur:
            for row in cur:
                try:
                    orig_area = row[fields_to_use.index(fld_orig_intsct_area)]
                    new_area = row[fields_to_use.index(fld_current_area)]
                    prorate_ratio = new_area / orig_area

                    orig_value = row[fields_to_use.index(f)]
                    new_value = orig_value * prorate_ratio
                    row[fields_to_use.index(f)] = new_value

                    cur.updateRow(row)
                except:
                    import pdb; pdb.set_trace()
        

if __name__ == '__main__':
    target = r'I:\Projects\Darren\PPA3_GIS\PPA3_GreenMeansGo.gdb\GreenZones2021_sample'
    intersecting = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Sugar_access_data_latest'
    output = 'I:\Projects\Darren\PPA3_GIS\PPA3_GreenMeansGo.gdb\TEST'

    fields = ['population']


    get_areapropl_values(target, intersecting, fields, output)

    
    
    