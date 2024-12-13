"""
Name: truckdata2hwylines.py
Purpose: Conflates point-based Caltrans truck data to NPMRDS links


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path

import arcpy, arcgisscripting

try:
    arcpy.Delete_management(arcpy.env.scratchGDB) # ensures a new, fresh scratch GDB is created to avoid any weird file-not-found errors
    print("Deleted arcpy scratch GDB to ensure reliability.")
except:
    pass

def field_cleanup(in_tbl, fields_to_keep):
    print(f"field cleanup for {in_tbl}...")
    for f in arcpy.ListFields(in_tbl):
        if f.name not in fields_to_keep:
            try:
                arcpy.DeleteField_management(in_tbl, f.name)
            except arcgisscripting.ExecuteError:
                print(f"\tWarning: did not delete required field {f.name}")
                pass

def conflate_truck_cnts(hwy_lines, truckvol_pts, input_count_field, other_truck_fields=None):

    '''Conflates data from truckvol_pts to line features in hwy_lines'''

    workspc = str(Path(hwy_lines).parent)
    arcpy.env.workspace = workspc
    arcpy.env.overwriteOutput = True

    f_jnfield = 'tmc'
    f_truckpct_in_scripts = 'Trk_Veh_Pc' # field actually used by scripts


    fl_hwy = 'fl_hwy'
    arcpy.MakeFeatureLayer_management(hwy_lines, fl_hwy)
    hwy_filter = "Route_Numb <> 0" # prevents incorrectly tagging truck count points to cross-streets by accident
    arcpy.SelectLayerByAttribute_management(fl_hwy, 'NEW_SELECTION', hwy_filter)

    
    fl_trkpnts = 'fl_trkpnts'
    arcpy.MakeFeatureLayer_management(truckvol_pts, fl_trkpnts)

    # spatial join truck point data to lines
    print("spatial joining truck point data to hwy lines")
    temp_result_fc_name = f"{str(Path(hwy_lines).name)}_TEMPwtruckvol"
    temp_result_fc_path = str(Path(arcpy.env.scratchGDB).joinpath(temp_result_fc_name))

    arcpy.SpatialJoin_analysis(target_features=fl_hwy, join_features=fl_trkpnts,
                               out_feature_class=temp_result_fc_path, match_option='CLOSEST',
                               search_radius='100 Feet')

    temp_result_fl = 'temp_result_fl'
    arcpy.MakeFeatureLayer_management(temp_result_fc_path, temp_result_fl)

    # rename field to one used by scripts
    arcpy.management.AlterField(temp_result_fl, field=input_count_field,
                                new_field_name=f_truckpct_in_scripts,
                                new_field_alias=f_truckpct_in_scripts)

    include_fields = [f_jnfield, f_truckpct_in_scripts]
    field_cleanup(temp_result_fl, fields_to_keep=include_fields)

    # join links with truck pct data to final NPMRDS data
    arcpy.SelectLayerByAttribute_management(fl_hwy, 'CLEAR_SELECTION')
    arcpy.management.AddJoin(fl_hwy, in_field=f_jnfield, join_table=temp_result_fl, 
                             join_field=f_jnfield, join_type='KEEP_ALL')
    
    # export to final FC
    final_fc_name  = f"{str(Path(hwy_lines).name)}_wtruckvol"
    arcpy.conversion.FeatureClassToFeatureClass(fl_hwy, workspc, final_fc_name)

    # clean out last unwanted fields
    original_fields = [f.name for f in arcpy.ListFields(hwy_lines)]
    final_keep_fields = [*include_fields, *original_fields]
    field_cleanup(final_fc_name, fields_to_keep=final_keep_fields)

    print(f"Resulting feature class: {Path(workspc).joinpath(final_fc_name)}")



if __name__ == '__main__':
    hwys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\NPMRDS_2023ppadata_final'
    truck_count_points = r'I:\Projects\Darren\PPA3_GIS\SHP\Truck__Volumes_AADT2022\HWY_Truck_Volumes_AADT.shp'
    truck_data_fields = 'TRK_PERCEN'

    conflate_truck_cnts(hwys, truck_count_points, truck_data_fields)