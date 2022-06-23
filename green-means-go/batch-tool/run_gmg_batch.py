"""
Name: gmg_batchrun.py
Purpose: For each green zone polygon in an input polygon feature class, compute:
    * person-weighted avg accessibility to services
    * person-weighted avg accessibility to jobs
    * land use diversity index (SACOG index)
    * percent of total road miles that are bike facilities



Author: Darren Conly
Last Updated: Jul 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import datetime as dt
import os
import csv

import arcpy
import pandas as pd

import accessibility_calcs as acc
import get_buff_netmiles as bikebuffmi
import mix_index_for_project as mixidx
import parameters as params

arcpy.overwriteOutput = True

def get_zone_data(polygon_fl_selection, data_year):
    """Compute applicable PPA metrics for single polygon representing green zone or other
    polygon-based analysis area.

    Args:
        in_poly (ESRI feature layer): selected subset within polygon feature layer
    """

    proj_type = params.ptype_area_agg
    
    temp_zone_fc = "memory/TEMP_green_zone_selection"
    if arcpy.Exists(temp_zone_fc): arcpy.Delete_management(temp_zone_fc)
    arcpy.management.CopyFeatures(polygon_fl_selection, temp_zone_fc)


    output_data = {}
    # calculate accessibility to jobs and services
    acc_layer = os.path.join(params.fgdb, params.accdata_fc)
    acc_data = acc.get_acc_data(fc_project=temp_zone_fc, fc_accdata=acc_layer, 
    project_type=proj_type, get_ej=False)


    # calculate land use diversity index
    parcels = os.path.join(params.fgdb, params.parcel_pt_fc_yr(data_year))
    lu_mix_index = mixidx.get_mix_idx(fc_parcel=parcels, fc_project=temp_zone_fc, 
                                    project_type=proj_type, buffered_pcls=False)

    # calculate percent of total road miles that are C2 bike lanes or C1 paths
    bikewy_mi = bikebuffmi.get_bikeway_mileage_share(project_fc=temp_zone_fc, proj_type=proj_type)

    # combine and return as single dict
    # import pdb; pdb.set_trace()
    for d in [acc_data, lu_mix_index, bikewy_mi]:
        output_data.update(d)

    return output_data

def get_gmg_batch_data(in_poly_fc, out_csv_path):
    """Computes relevant Green Zone data for input polygon layer

    Args:
        in_poly_fc (_type_): polygons representing Green Zones
        out_csv_path (_type_): file path for CSV output containing PPA data for each green zone
    """

    data_year = 2016

    in_poly_fl = "in_poly_fl"
    f_id = "GZID"
    f_jur = "Juris"
    f_gzname = "GZName"
    poly_fl_fields = [f_id, f_jur, f_gzname]
    arcpy.MakeFeatureLayer_management(in_poly_fc, in_poly_fl)
    zone_cnt = arcpy.GetCount_management(in_poly_fl)[0]
    
    print(f"Beginning analysis of {zone_cnt} zones...")
    with open(out_csv_path, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        with arcpy.da.SearchCursor(in_poly_fl, poly_fl_fields) as cur:
            i = 0
            for row in cur:
                try:
                    zone_id = row[poly_fl_fields.index(f_id)]
                    zone_jur = row[poly_fl_fields.index(f_jur)]
                    zone_name = row[poly_fl_fields.index(f_gzname)]
                    sql_getzone = f"{f_id} = '{zone_id}'"
                    arcpy.SelectLayerByAttribute_management(in_poly_fl, where_clause=sql_getzone)
                    zone_data = get_zone_data(in_poly_fl, data_year)

                    output_dict = {f_id: zone_id, f_jur: zone_jur, f_gzname: zone_name}
                    output_dict.update(zone_data)

                    if i == 0:
                        headers = list(output_dict.keys())
                        writer.writerow(headers)

                    data_row = list(output_dict.values())
                    writer.writerow(data_row)

                    i += 1

                    if i % 10 == 0:
                        print(f"{i} of {zone_cnt} zones processed...")

                except:
                    import pdb; pdb.set_trace()




if __name__ == '__main__':
    # SHP or FC of green zone polygons
    fc_zones = r'I:\Projects\Darren\PPA3_GIS\PPA3_GreenMeansGo.gdb\GreenZones2021'
    output_dir = r'I:\Projects\Darren\PPA3_GIS\CSV\GMG'

#=============================RUN SCRIPT=================================
    # specify output file path
    sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_csv = f'gmg_batch_results{sufx}.csv'
    out_path = os.path.join(output_dir, out_csv)

    get_gmg_batch_data(fc_zones, out_path)

    print(f"Success! Output file is {out_path}")
