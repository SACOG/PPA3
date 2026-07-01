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
from utils import utils


def _prorate_acc_polygons(fc_project, fc_accdata_seln, project_type, sufx):
    '''Intersects accessibility polygons with project area and prorates the population
    field by (intersected area / original area). Returns path to intersected FC.

    For line projects: buffers the line to bg_search_dist first, then intersects.
    For polygon (area_agg) projects: intersects directly with the project polygon.
    Prorating ensures boundary block groups are only weighted by their overlap fraction.
    '''
    fld_orig_area = 'AREA_origl'
    fc_buffer    = os.path.join(arcpy.env.scratchGDB, f'TEMP_acc_buff{sufx}')
    fc_intersect = os.path.join(arcpy.env.scratchGDB, f'TEMP_acc_intsct{sufx}')

    for fc in [fc_buffer, fc_intersect]:
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)

    if fld_orig_area not in [f.name for f in arcpy.ListFields(fc_accdata_seln)]:
        arcpy.management.AddField(fc_accdata_seln, fld_orig_area, 'DOUBLE')
    with arcpy.da.UpdateCursor(fc_accdata_seln, [fld_orig_area, 'SHAPE@AREA']) as cur:
        for row in cur:
            row[0] = row[1]
            cur.updateRow(row)

    if project_type == params.ptype_area_agg:
        target_fc = fc_project
    else:
        arcpy.analysis.Buffer(fc_project, fc_buffer, params.bg_search_dist)
        target_fc = fc_buffer

    arcpy.analysis.Intersect([fc_accdata_seln, target_fc], fc_intersect)

    with arcpy.da.UpdateCursor(fc_intersect, [fld_orig_area, 'SHAPE@AREA', params.col_pop]) as cur:
        for row in cur:
            orig_area = row[0]
            if orig_area and orig_area > 0:
                row[2] = row[2] * (row[1] / orig_area)
            cur.updateRow(row)

    if arcpy.Exists(fc_buffer):
        arcpy.Delete_management(fc_buffer)

    return fc_intersect


def get_acc_data(fc_project, fc_accdata, project_type, get_ej=False):
    '''Calculate average accessibility to selected destination types for all
    polygons that either intersect the project line or are within a community type polygon.
    Population weight is pro-rated by the fraction of each accessibility polygon that
    overlaps the project buffer, so boundary polygons are not over-counted.'''

    arcpy.AddMessage("Calculating accessibility metrics...")

    sufx = int(perf()) + 1
    fl_accdata   = os.path.join('memory', f'fl_accdata{sufx}')
    fl_project   = 'fl_project'
    fc_temp_seln = os.path.join(arcpy.env.scratchGDB, f'TEMP_acc_seln{sufx}')

    for fc in [fl_project, fl_accdata]:
        if arcpy.Exists(fc): arcpy.Delete_management(fc)

    arcpy.MakeFeatureLayer_management(fc_project, fl_project)
    arcpy.MakeFeatureLayer_management(fc_accdata, fl_accdata)

    arcpy.SelectLayerByLocation_management(fl_accdata, 'INTERSECT', fl_project,
                                           params.bg_search_dist, 'NEW_SELECTION')
    arcpy.CopyFeatures_management(fl_accdata, fc_temp_seln)

    fc_intersect = _prorate_acc_polygons(fl_project, fc_temp_seln, project_type, sufx)

    accdata_fields = [params.col_geoid, params.col_acc_ej_ind, params.col_pop] + params.acc_cols_ej
    accdata_df = utils.esri_object_to_df(fc_intersect, accdata_fields)

    out_dict = {}
    if get_ej:
        for col in params.acc_cols_ej:
            col_wtd    = f'{col}_wtd'
            col_ej_pop = f'{params.col_pop}_EJ'
            accdata_df[col_wtd]    = accdata_df[col] * accdata_df[params.col_pop] * accdata_df[params.col_acc_ej_ind]
            accdata_df[col_ej_pop] = accdata_df[params.col_pop] * accdata_df[params.col_acc_ej_ind]
            tot_ej_pop = accdata_df[col_ej_pop].sum()
            out_dict[f'{col}_EJ'] = accdata_df[col_wtd].sum() / tot_ej_pop if tot_ej_pop > 0 else 0
    else:
        total_pop = accdata_df[params.col_pop].sum()
        for col in params.acc_cols:
            if total_pop <= 0:
                out_dict[col] = accdata_df[col].mean()
            else:
                accdata_df[f'{col}_wtd'] = accdata_df[col] * accdata_df[params.col_pop]
                out_dict[col] = accdata_df[f'{col}_wtd'].sum() / total_pop

    for fc in [fc_temp_seln, fc_intersect]:
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)

    return out_dict


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
    
    fc_project_line = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Polylines'
    fc_accessibility_data = params.accdata_fc
    str_project_type = params.ptype_arterial
    
    dict_data = get_acc_data(fc_project_line, fc_accessibility_data, str_project_type)
    arcpy.AddMessage(dict_data)
    
