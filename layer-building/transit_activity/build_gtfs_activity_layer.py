"""
Name: build_gtfs_activity_layer.py
Purpose: Build stop point layer with unique stop locations and number of time per day
    That each point is served by a transit vehicle.

    Used for getting transit density within an area.


Author: Darren Conly
Last Updated: Aug 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import os

import pandas as pd
import arcpy

from gtfs_processor_latest import MakeGTFSGISData

def filter_service(op_gtfs_folder, dayname_field, stops_fc):
    try:
        cal_file = 'calendar.txt'
        df_calendar = pd.read_csv(os.path.join(op_gtfs_folder, cal_file))
        df_cal_filtered = df_calendar[df_calendar[dayname_field] == 1]

        f_sid_name = 'service_id'
        f_sid_type = [f.type for f in arcpy.ListFields(stops_fc) if f.name == f_sid_name][0]

        if f_sid_type == 'String':
            svcs_to_use = tuple([f'{i}' for i in df_cal_filtered[f_sid_name].unique()])
            if len(svcs_to_use) == 1: svcs_to_use = f"('{svcs_to_use[0]}')"
        else:
            svcs_to_use = tuple([i for i in df_cal_filtered[f_sid_name].unique()])
            if len(svcs_to_use) == 1: svcs_to_use = f"({svcs_to_use[0]})"

        sql = f"service_id IN {svcs_to_use}"

        fl_stops = "fl_stops"
        arcpy.management.MakeFeatureLayer(stops_fc, fl_stops)
        arcpy.management.SelectLayerByAttribute(fl_stops, "NEW_SELECTION", sql)

        out_fc = f"{stops_fc}_{dayname_field}"
        arcpy.CopyFeatures_management(fl_stops, out_fc)

        print(f"filtered stops to only reflect service operating on {dayname_field} to {out_fc}")
    except:
        import pdb; pdb.set_trace()

def make_stop_points(gtfs_folder, output_fgdb):
    
    # Year flag only used in output feature class and file names, not used for any calculations
    # No specific format needed, but be as concise as possible
    year = 'Fall2019' 

    gtfso = MakeGTFSGISData(gtfs_folder, output_fgdb, year)
    gtfso.make_stop_pts()

    out_path = os.path.join(output_fgdb, gtfso.fc_stop_pts)
    print(f"successfully exported GTFS data from {gtfs_folder} to {output_fgdb}...")

    filter_service(gtfs_folder, 'monday', out_path)



if __name__ == '__main__':
    results_fgdb = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb'
    gtfs_root_dir = r'Q:\SACSIM23\Network\TransitNetwork\GTFS'
    gtfs_op_folders = ['Amtrak', 'Auburn', 'ElDorado', 'ETRANS', 'PCT', 'Roseville',
                        'SRTD', 'unitrans', 'YoloBus', 'YubaSutter']
    gtfs_op_folders = ['Amtrak']

    for op in gtfs_op_folders:
        op_path = os.path.join(gtfs_root_dir, op)
        make_stop_points(op_path, results_fgdb)
