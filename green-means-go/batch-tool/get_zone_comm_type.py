"""
Name: get_zone_comm_type.py
Purpose: Retrieve the community type that a Green Zone polygon is in.
    If a Green Zone intersects more than 1 community type, tag it with the 
    community type that has the most overlap/intersection with the Green Zone


Author: Darren Conly
Last Updated: Jul 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os

import arcpy

import parameters as params

def get_comm_type(zone_fc, comm_type_fc, name_field):

    temp_intersect_fc = os.path.join(arcpy.env.scratchGDB, "TEMP_intersect_fc")
    if arcpy.Exists(temp_intersect_fc): arcpy.Delete_management(temp_intersect_fc)

    arcpy.Intersect_analysis([zone_fc, comm_type_fc], temp_intersect_fc)

    ctvals_dict = {} # {comm_type_name: total_area} for all comm types intersecting the zone

    f_area = "SHAPE@AREA"
    
    with arcpy.da.SearchCursor(temp_intersect_fc, [name_field, f_area]) as cur:
        for row in cur:
            ctname = row[0]
            area = row[1]
            if ctvals_dict.get(ctname) is None: # if ctype isn't in dict yet, add it with it's area
                ctvals_dict[ctname] = area
            else:
                ctvals_dict[ctname] += area # if ct is already in dict, then just add the current record's area to the dict's value
    
    maxval_dict = {k:v for k, v in ctvals_dict.items() if v == max(ctvals_dict.values())}    
    out_ctype = [k for k in maxval_dict.keys()][0]  

    output_dict = {params.col_ctype: out_ctype}

    return output_dict



if __name__ == '__main__':
    z_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3_GreenMeansGo.gdb\GreenZones2021_SacCity1_old'
    comm_types_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\comm_type_juris_latest'
    comm_type_namefield = 'comm_type_ppa'
    
    test_result = get_comm_type(z_fc, comm_types_fc, comm_type_namefield)
    print(test_result)