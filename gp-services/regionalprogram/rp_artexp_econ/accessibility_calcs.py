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
import arcpy

import parameters as params
import utils.utils as ut


def get_acc_data(fc_project, fc_accdata, project_type, get_ej=False):
    '''Calculate average accessibility to selected destination types for all
    polygons that either intersect the project line or are within a community type polygon.
    Average accessibility is weighted by each polygon's population.'''
    
    arcpy.AddMessage("Calculating accessibility metrics...")
    
    sufx = int(perf()) + 1
    fl_accdata = os.path.join('memory','fl_accdata{}'.format(sufx))
    fl_project = 'fl_project'

    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)

    if arcpy.Exists(fl_accdata): arcpy.Delete_management(fl_accdata)
    arcpy.MakeFeatureLayer_management(fc_accdata, fl_accdata)

    # select polygons that intersect with the project line
    searchdist = 0 if project_type == params.ptype_area_agg else params.bg_search_dist
    arcpy.SelectLayerByLocation_management(fl_accdata, "INTERSECT", fl_project, searchdist, "NEW_SELECTION")

    # read accessibility data from selected polygons into a dataframe
    accdata_fields = [params.col_geoid, params.col_acc_ej_ind, params.col_pop] + params.acc_cols_ej
    accdata_df = ut.esri_object_to_df(fl_accdata, accdata_fields)

    # get pop-weighted accessibility values for all accessibility columns

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
    
