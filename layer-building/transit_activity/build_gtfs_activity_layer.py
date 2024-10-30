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
from pathlib import Path
import os
import zipfile

import pandas as pd
import arcpy

from gtfs_processor_latest import MakeGTFSGISData

def load_zip_item_to_df(zipdir, filename):
    # Open the zip file
    with zipfile.ZipFile(zipdir, 'r') as zip_ref:
        # Extract the file you want to read
        with zip_ref.open(filename) as file:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(file)

    return df

def filter_service(op_gtfs_zip, dayname_field, stops_fc):
    stops_fc = str(stops_fc) # ESRI tools don't like Path objects; convert to string
    try:
        # df_calendar = pd.read_csv(Path(op_gtfs_folder).joinpath('calendar.txt'))
        df_calendar = load_zip_item_to_df(op_gtfs_zip, 'calendar.txt')
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

        return out_fc
    except:
        import pdb; pdb.set_trace()

def make_stop_points(gtfs_zip, output_fgdb, svc_year):
    
    # Year flag only used in output feature class and file names, not used for any calculations
    # No specific format needed, but be as concise as possible

    gtfso = MakeGTFSGISData(gtfs_zip, output_fgdb, svc_year)
    gtfso.make_stop_pts()

    out_path = Path(output_fgdb).joinpath(gtfso.fc_stop_pts)
    print(f"successfully exported GTFS data from {gtfs_zip} to {out_path}...")

    filter_fc_path = filter_service(gtfs_zip, 'monday', out_path)

    return str(filter_fc_path)



if __name__ == '__main__':
    results_fgdb = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb'
    gtfs_root_dir = r'I:\Projects\Darren\PPA3_GIS\ConveyalLayers\GTFS\datemod_versions'
    data_year = 2024

    # ==============RUN SCRIPT=======================
    zips = [opzip for opzip in Path(gtfs_root_dir).glob('*.zip')]
    results = []
    for src_zip in zips:
        result = make_stop_points(src_zip, results_fgdb, data_year)
        results.append(result)

    # merge into single regional file
    fc_results_merge = str(Path(results_fgdb).joinpath(f"transit_activity_weekdays{data_year}"))
    results_weekday = [result_path for result_path in results if 'monday' in result_path]

    arcpy.management.Merge(inputs=results_weekday, output=fc_results_merge)
    print(f"Success. Results in {fc_results_merge}")
