"""
Name: parcel_data.py
Purpose: create temporary feature class containing parcels within the selected
    buffer area. 


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

def get_buffer_parcels(fc_pclpt, fc_project, buffdist, project_type, data_year, parcel_cols=None):
    arcpy.AddMessage(f"Generating temp parcel file of parcels in project vicinity or zone for year {data_year}...")
    sufx = int(perf()) + 1
    fl_parcel = os.path.join('memory',f'fl_parcel{sufx}')
    fl_project = "fl_project"
    out_fc = f"buff_pcl_pts{data_year}{sufx}"

    if arcpy.Describe(arcpy.env.scratchGDB).dataType == 'Folder':
        # expectation that scratch GDB is a GDB, not a folder, but sometimes this messes up.
        arcpy.AddMessage(f'WARNING, {arcpy.env.scratchGDB} is a folder, not a file geodatabase. Pausing for diagnosis...')
        import pdb; pdb.set_trace()

    out_fc_path = os.path.join(arcpy.env.scratchGDB, out_fc)
    if arcpy.Exists(out_fc_path): arcpy.Delete_management(out_fc_path)
    
    if arcpy.Exists(fl_parcel): arcpy.Delete_management(fl_parcel)
    arcpy.MakeFeatureLayer_management(fc_pclpt, fl_parcel)
    
    if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
    arcpy.MakeFeatureLayer_management(fc_project, fl_project)    

    buff_dist = 0 if project_type == params.ptype_area_agg else buffdist

    arcpy.SelectLayerByLocation_management(fl_parcel, "WITHIN_A_DISTANCE", fl_project, buff_dist)
    arcpy.conversion.FeatureClassToFeatureClass(fl_parcel, arcpy.env.scratchGDB, out_fc)

    return out_fc_path




if __name__ == '__main__':

    dyear = 2016
    pcl_fc = params.parcel_pt_fc_yr(dyear)
    pcl_project = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'
    buffdist = 1320
    projtype = params.ptype_arterial

    #=============RUN SCRIPT=========================
    os.chdir(r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb')
    print(arcpy.env.scratchGDB)

    result = get_buffer_parcels(fc_pclpt=pcl_fc, fc_project=pcl_project, 
    buffdist=buffdist, project_type=projtype, data_year = dyear, parcel_cols=None)

    print(result)

