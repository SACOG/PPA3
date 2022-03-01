
"""
Approach:
1 - load all numbers from all reports
2 - line-by-line, digit-by-digit populating of JSON file
3 - get it to work, refactor later as needed.
"""
import datetime as dt
from time import perf_counter as perf
import os
import json
import pandas as pd
import arcpy
# arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

import parameters as params
from commtype import get_proj_ctype
from parcel_data import get_buffer_parcels
import chart_job_du_tot
import chart_accessibility
import chart_mixindex


def make_vmt_report_artexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_ReduceVMT_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        json_loaded = json.load(j_in)

    # get project community type
    project_commtype = get_proj_ctype(project_fc, params.comm_types_fc)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc land use buffer values 
    for i, year in enumerate(data_years):
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        chart_job_du_tot.update_json(json_loaded, data_year=year, order_val=i, pcl_pt_fc=in_pcl_pt_fc, 
                                    project_fc=project_fc, project_type=ptype)

    # calc accessibility numbers and update JSON chart with it
    chart_accessibility.update_json(json_loaded=json_loaded, fc_project=project_fc, project_type=ptype,
                                    project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
                                    k_chart_title="Base Year Service Accessibility")


    # calc mix index
    for i, year in enumerate(data_years):
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        chart_mixindex.update_json(json_loaded, fc_project=project_fc, fc_parcel=in_pcl_pt_fc,
                                    data_year=year, proj_type=ptype, project_commtype=project_commtype,
                                    aggval_csv=params.aggval_csv)

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"VMTReport{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(json_loaded, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============

     # "SACOG_ReduceVMT_template.json"
    output_dir = arcpy.env.scratchFolder
    arcpy.env.workspace = params.fgdb

    # specify project line feature class and attributes
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge' # arcpy.GetParameterAsText(0)  
    project_name = 'TestStockton' # arcpy.GetParameterAsText(1)

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    result_path = make_vmt_report_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


