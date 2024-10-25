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
from pathlib import Path
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder


from time import perf_counter as perf
import arcpy

import parameters as params


def get_ctype_from_ix(ix_fc, quant_field):
    # grab community type based on which ctype has most overlap with project line (or if not using line, then buffer around project)
    fields = ['OBJECTID', quant_field, params.col_ctype]
    ctype_size_dict = {}

    with arcpy.da.SearchCursor(ix_fc, fields) as cur:
        for row in cur:
            ctype = row[fields.index(params.col_ctype)]
            piece_size = row[fields.index(quant_field)]
        
            if ctype_size_dict.get(ctype) is None:
                ctype_size_dict[ctype] = piece_size
            else:
                ctype_size_dict[ctype] += piece_size

    maxval = max([v for k, v in ctype_size_dict.items()])
    proj_ctype = [k for k, v in ctype_size_dict.items() if v == maxval][0]

    return proj_ctype

def get_proj_ctype(in_project_fc, commtypes_fc):
    '''Get project community type, based on which community type has most spatial overlap with project'''
    ts = int(perf())
    scratch_gdb = Path(arcpy.env.scratchGDB)
    temp_intersect_fc = str(scratch_gdb.joinpath(f'temp_intersect_fc{ts}'))
    if arcpy.Exists(temp_intersect_fc): arcpy.Delete_management(temp_intersect_fc)

    arcpy.Intersect_analysis([in_project_fc, commtypes_fc], temp_intersect_fc, "ALL", 0, "LINE")
    
    # debugging messages to find out why ctype tagging intermittently fails
    intersect_cnt = int(arcpy.GetCount_management(temp_intersect_fc)[0])
    in_project_cnt = int(arcpy.GetCount_management(in_project_fc)[0])
    
    if intersect_cnt > 0:
        proj_ctype = get_ctype_from_ix(temp_intersect_fc, quant_field='SHAPE@LENGTH')
    else:
        # ideally we want to get ctype based on what the project *line* most overlaps with. But if that's not possible,
        # we make buffer around line and see which ctype most overlaps with the buffer
        temp_pbuff_fc = str(scratch_gdb.joinpath(f'pbuff{ts}'))
        temp_pbuff_ix_fc = str(scratch_gdb.joinpath(f'pbuff_intersect{ts}'))
        for fc in [temp_pbuff_fc, temp_pbuff_ix_fc]:
            if arcpy.Exists(fc): arcpy.Delete_management(fc)
        arcpy.analysis.Buffer(in_project_fc, temp_pbuff_fc, buffer_distance_or_field=200) # assume 200ft buffer to have intersection with adjacent ctypes
        arcpy.Intersect_analysis([temp_pbuff_fc, commtypes_fc], temp_pbuff_ix_fc, "ALL", 0, "INPUT")
        intersect_cnt_buff = int(arcpy.GetCount_management(temp_pbuff_ix_fc)[0])

        if intersect_cnt_buff == 0:
            raise ValueError("ERROR: No Community Type identified for project. \n{} project line features." \
                             " {} features in intersect layer.".format(in_project_cnt, intersect_cnt))
        else:
            proj_ctype = get_ctype_from_ix(temp_pbuff_ix_fc, quant_field='SHAPE@AREA')
        
    return proj_ctype



if __name__ == '__main__':
    # test_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_HoweAve' # sr3857
    # test_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge' # sr 2226, cross multiple ctypes
    test_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestJefferson' # sr3857, contained in single ctype

    test_commtypes_fc = r"\\arcserver-svr\D\PPA_v2_SVR\PPA2_GIS_SVR\owner_PPA.sde\comm_type_jurspec_dissolve"
    # import pdb; pdb.set_trace()

    output = get_proj_ctype(test_fc, test_commtypes_fc)
    print(output)


