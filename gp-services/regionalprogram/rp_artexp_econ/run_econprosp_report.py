
"""
Approach:
1 - load all numbers from all reports
2 - line-by-line, digit-by-digit populating of JSON file
3 - get it to work, refactor later as needed.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import datetime as dt
import json
import arcpy


import parameters as params
from commtype import get_proj_ctype
from parcel_data import get_buffer_parcels
from landuse_buff_calcs import LandUseBuffCalcs
import chart_accessibility
import chart_lu_acre_change


def make_econ_report_artexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_EconProsperity_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = get_proj_ctype(project_fc, params.comm_types_fc)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc K-12 enrollment in base year
    base_buff_pcl_fc = parcel_fc_dict[data_years[0]]
    year_dict = LandUseBuffCalcs(base_buff_pcl_fc, fc_project, project_commtype, [params.col_k12_enr], 
                buffered_pcls=True).point_sum()
    k12_enr_val = year_dict[params.col_k12_enr]
    loaded_json["K12 Enrollment"] = k12_enr_val


    # calc increase in jobs between base and future year
    out_job_data = []

    for i, years in enumerate(data_years):
        in_pcl_pt_fc = parcel_fc_dict[year] # use parcels within buffer, not entire region of parcels
        year_dict = LandUseBuffCalcs(in_pcl_pt_fc, fc_project, project_commtype, [params.col_emptot], 
                    buffered_pcls=True).point_sum()
        out_job_data.append(year_dict[params.col_emptot])

    job_change = out_job_data[-1] - out_job_data[0]
    loaded_json["Total new jobs added"] = job_change

    # calc change in ag acreage
    for i, year in enumerate(data_years):
        arcpy.AddMessage(f"calculating Ag land use acres for {year}")
        in_pcl_poly_fc = params.parcel_poly_fc_yr(year)
        chart_lu_acre_change.update_json(json_loaded=loaded_json, data_year=year, order_val=i, fc_poly_parcels=in_pcl_poly_fc,
                                        project_fc=fc_project, project_type=project_type, in_lu_type='Agriculture',
                                        k_chart_title="Change in Ag acreage")

    # access to jobs chart update
    chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
                                    project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
                                    k_chart_title="Access to jobs", destination_type='alljob')

    # access to edu facilities chart update
    chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
                                    project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
                                    k_chart_title="Education Facility", destination_type='edu')


    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"EconProspRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)  # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'
    project_name = arcpy.GetParameterAsText(1)  # 'TestTruxelBridge'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_econ_report_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


