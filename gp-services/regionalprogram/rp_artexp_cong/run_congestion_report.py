"""
Name: run_congestion_report.py
Purpose: calculate numbers for the congestion subreport and produce applicable charts.


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
import json
import arcpy


import parameters as params
import parcel_data
import chart_job_du_tot
import chart_congestion
import npmrds_data_conflation as npmrds


def make_congestion_rpt_artexp(fc_project, project_name, project_type, aadt):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_ReduceCongestion_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    # for year in data_years:
    #     in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
    #     pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
    #                         buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
    #     parcel_fc_dict[year] = pcl_buff_fc

    # # calc land use buffer values (job + du totals)
    # for i, year in enumerate(data_years):
    #     in_pcl_pt_fc = parcel_fc_dict[year]
    #     chart_job_du_tot.update_json(json_loaded=loaded_json, data_year=year, order_val=i, pcl_pt_fc=in_pcl_pt_fc, 
    #                                 project_fc=project_fc, project_type=ptype)

    # get congestion data
    congn_data = npmrds.get_npmrds_data(fc_project, project_type)
    import pdb; pdb.set_trace()

    cong_rpt_obj = chart_congestion.CongestionReport(congn_data, loaded_json)

    cong_rpt_obj.update_all_congestion_data()

    # update AADT
    loaded_json["projectAADT"] = aadt

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CongestnRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    # project_fc = arcpy.GetParameterAsText(0)
    # project_name = arcpy.GetParameterAsText(1) 
    # proj_aadt = int(arcpy.GetParameterAsText(2))

    # testing parameters
    project_fc = 'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\X_St_Oneway'  # 
    project_name = 'XSt' #  
    proj_aadt = 32000 # 

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_congestion_rpt_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype, aadt=proj_aadt)

    arcpy.SetParameterAsText(3, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


