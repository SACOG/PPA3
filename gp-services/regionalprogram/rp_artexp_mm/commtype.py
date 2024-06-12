"""
Name: commtype.py
Purpose: Get project community type, based on which community type has most spatial overlap with project


Author: Darren Conly
Last Updated: Feb 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder


from time import perf_counter as perf
import arcpy

import parameters as params

def get_proj_ctype(in_project_fc, commtypes_fc):
    '''Get project community type, based on which community type has most spatial overlap with project'''
    ts = int(perf())
    temp_intersect_fc = os.path.join(arcpy.env.scratchGDB, f'temp_intersect_fc{ts}')
    if arcpy.Exists(temp_intersect_fc): arcpy.Delete_management(temp_intersect_fc)

    arcpy.Intersect_analysis([in_project_fc, commtypes_fc], temp_intersect_fc, "ALL", 0, "LINE")
    
    # debugging messages to find out why ctype tagging intermittently fails
    intersect_cnt = int(arcpy.GetCount_management(temp_intersect_fc)[0])
    in_project_cnt = int(arcpy.GetCount_management(in_project_fc)[0])
    
    len_field = 'SHAPE@LENGTH'
    fields = ['OBJECTID', len_field, params.col_ctype]
    ctype_dist_dict = {}
    
    with arcpy.da.SearchCursor(temp_intersect_fc, fields) as cur:
        for row in cur:
            ctype = row[fields.index(params.col_ctype)]
            seg_len = row[fields.index(len_field)]
        
            if ctype_dist_dict.get(ctype) is None:
                ctype_dist_dict[ctype] = seg_len
            else:
                ctype_dist_dict[ctype] += seg_len
    try:
        maxval = max([v for k, v in ctype_dist_dict.items()])
        proj_ctype = [k for k, v in ctype_dist_dict.items() if v == maxval][0]

        return proj_ctype
    except:
        raise ValueError("ERROR: No Community Type identified for project. \n{} project line features." \
        " {} features in intersect layer.".format(in_project_cnt, intersect_cnt))



if __name__ == '__main__':
    pass


