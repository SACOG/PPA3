"""
Name: run_congestion_report.py
Purpose: calculate numbers for the reduce-VMT subreport and produce applicable charts.


Author: Darren Conly
Last Updated: Feb 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import datetime as dt
from time import perf_counter as perf
import json
import pandas as pd
import arcpy


import parameters as params
from commtype import get_proj_ctype
from parcel_data import get_buffer_parcels
import chart_job_du_tot
import chart_accessibility
import chart_mixindex


def make_congestion_rpt_artexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_ReduceCongestion_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc land use buffer values (job + du totals)
    for i, year in enumerate(data_years):
        in_pcl_pt_fc = parcel_fc_dict[year]
        chart_job_du_tot.update_json(json_loaded=loaded_json, data_year=year, order_val=i, pcl_pt_fc=in_pcl_pt_fc, 
                                    project_fc=project_fc, project_type=ptype)

    # calc numbers for speeds chart
    # calc numbers for reliability chart
    # calc congestion ratio values for table



    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"VMTReport{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)  # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'
    project_name = arcpy.GetParameterAsText(1) # 'TestTruxelBridge'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_congestion_rpt_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


