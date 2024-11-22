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

import arcpy



def conflate_truck_cnts(hwy_lines, truckvol_pts, input_count_field, other_truck_fields=None):

    '''Conflates data from truckvol_pts to line features in hwy_lines'''

    workspc = str(Path(hwy_lines).parent)
    arcpy.env.workspace = workspc
    arcpy.env.overwriteOutput = True

    fl_hwy = 'fl_hwy'
    arcpy.MakeFeatureLayer_management(hwy_lines, fl_hwy)
    hwy_filter = "Route_Numb <> 0" # prevents incorrectly tagging truck count points to cross-streets by accident
    arcpy.SelectLayerByAttribute_management(fl_hwy, 'NEW_SELECTION', hwy_filter)

    
    fl_trkpnts = 'fl_trkpnts'
    arcpy.MakeFeatureLayer_management(truckvol_pts, fl_trkpnts)

    # spatial join truck point data to lines
    print("spatial joining truck point data to hwy lines")
    result_fc = f"{str(Path(hwy_lines).name)}_wtruckvol"
    arcpy.SpatialJoin_analysis(target_features=fl_hwy, join_features=fl_trkpnts,
                               out_feature_class=result_fc, match_option='CLOSEST',
                               search_radius='100 Feet')

    result_fl = 'result_fl'
    arcpy.MakeFeatureLayer_management(result_fc, result_fl)

    # rename field to one used by scripts
    f_truckpct_in_scripts = 'Trk_Veh_Pc' # field actually used by scripts
    arcpy.management.AlterField(result_fl, field=input_count_field,
                                new_field_name=f_truckpct_in_scripts,
                                new_field_alias=f_truckpct_in_scripts)


    # delete unwanted fields
    hwyfields = [f.name for f in arcpy.ListFields(hwy_lines)]
    include_fields = [*hwyfields, f_truckpct_in_scripts]
    if other_truck_fields:
        include_fields = [*include_fields, *other_truck_fields]

    for f in arcpy.ListFields(result_fl):
        if f.name not in include_fields:
            arcpy.DeleteField_management(result_fl, f.name)

    print(f"Resulting feature class: {Path(workspc).joinpath(result_fc)}")





if __name__ == '__main__':
    hwys = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\NPMRDS_2023_NHS_SACOG'
    truck_count_points = r'I:\Projects\Darren\PPA3_GIS\SHP\Truck__Volumes_AADT2022\HWY_Truck_Volumes_AADT.shp'
    truck_data_fields = 'TRK_PERCEN'

    conflate_truck_cnts(hwys, truck_count_points, truck_data_fields)