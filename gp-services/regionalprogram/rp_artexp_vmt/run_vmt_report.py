"""
Name: run_vmt_report.py
Purpose: Run reduce-VMT subreport for arterial and transit expansion projects


Author: Darren Conly
Last Updated: Mar 2022
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
import arcpy
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space


import parameters as params
import commtype
import parcel_data
import chart_job_du_tot
import chart_accessibility
import chart_mixindex
from utils import utils as utils

# modules not used in main script, but imported to ensure they publish to server.
# more details see https://community.esri.com/t5/arcgis-pro-questions/scripts-not-used-by-main-script-do-not-upload-when/m-p/1489802
import landuse_buff_calcs, accessibility_calcs, mix_index_for_project, get_agg_values

def make_vmt_report_artexp(input_dict):

    uis = params.user_inputs
    project_fc = input_dict[uis.geom]
    proj_type = input_dict[uis.ptype]
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_ReduceVMT_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [params.base_year, params.future_year]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=project_fc,
                            buffdist=lu_buffdist_ft, project_type=proj_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc land use buffer values 
    d_lubuff = {}
    for i, year in enumerate(data_years):
        in_pcl_pt_fc = parcel_fc_dict[year]
        d_jobdu = chart_job_du_tot.update_json(json_loaded=loaded_json, data_year=year, order_val=i, pcl_pt_fc=in_pcl_pt_fc, 
                                    project_fc=project_fc, project_type=proj_type)

        # {f"jobs": jobs, f"dwellingUnits": du}
        d_lubuff[year] = d_jobdu
    
    job_base = d_lubuff[data_years[0]]["jobs"]
    job_future = d_lubuff[data_years[1]]["jobs"]
    du_base = d_lubuff[data_years[0]]["dwellingUnits"]
    du_future = d_lubuff[data_years[1]]["dwellingUnits"]

    # calc accessibility numbers and update JSON chart with it
    # update_json(json_loaded, fc_project, project_type, project_commtype, destination_type, weight_pop, aggval_csv, k_chart_title)
    acc_data = chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=proj_type,
                                    project_commtype=project_commtype, destination_type='nonwork', weight_pop='pop', 
                                    aggval_csv=params.aggval_csv, k_chart_title="Base Year Service Accessibility")


    # calc mix index
    d_mixidx = {}
    for i, year in enumerate(data_years):
        in_pcl_pt_fc = parcel_fc_dict[year]
        dy_mixidx = chart_mixindex.update_json(json_loaded=loaded_json, fc_project=project_fc, fc_parcel=in_pcl_pt_fc,
                                    data_year=year, proj_type=proj_type, project_commtype=project_commtype,
                                    aggval_csv=params.aggval_csv)
        
        # dy_mixidx = {'mix_index': <mix index val>}
        d_mixidx[year] = dy_mixidx

    mixidx_base = d_mixidx[data_years[0]][params.mix_idx_col]
    mixidx_future = d_mixidx[data_years[1]][params.mix_idx_col]

    # log to archive GDB tables
    project_id = utils.get_project_uid(input_dict[uis.name], proj_type, input_dict[uis.jur], input_dict[uis.email])

    data_to_log = {
        'project_uid': project_id, 'jobs_base': job_base, 
        'jobs_future': job_future, 'du_base': du_base, 
        'du_future': du_future, 'lumix_base': mixidx_base, 
        'lumix_future': mixidx_future, 'acc_svc_walk': acc_data['walk_nonwork'], 
        'acc_svc_bike': acc_data['bike_nonwork'], 
        # 'acc_svc_drive': acc_data['drive_nonwork'], # as of PPA3.1, no longer reporting drive-to-nonwork destinations
        'acc_svc_pubtrn': acc_data['transit_nonwork'] 
    }


    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb,'rp_artexp_vmt'))

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"VMTReport{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============

    # inputs from tool interface
    # project_fc = arcpy.GetParameterAsText(0)
    # project_name = arcpy.GetParameterAsText(1)
    # jurisdiction = arcpy.GetParameterAsText(2)
    # project_type = arcpy.GetParameterAsText(3)
    # perf_outcomes = arcpy.GetParameterAsText(4)
    # aadt = arcpy.GetParameterAsText(5)
    # posted_spd = arcpy.GetParameterAsText(6)
    # pci = arcpy.GetParameterAsText(7)
    # email = arcpy.GetParameterAsText(8)

    # hard-coded vals for testing
    project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\X_St_Oneway'
    project_name = 'XSt'
    jurisdiction = 'Sac'
    project_type = 'Arterial Expansion'
    perf_outcomes = 'TEST;Reduce Congestion;Reduce VMT'
    aadt = 20000
    posted_spd = 65
    pci = 80
    email = 'fake@test.com'

    uis = params.user_inputs
    input_parameter_dict = {
        uis.geom: project_fc,
        uis.name: project_name,
        uis.jur: jurisdiction,
        uis.ptype: project_type,
        uis.perf_outcomes: perf_outcomes,
        uis.aadt: aadt,
        uis.posted_spd: posted_spd,
        uis.pci: pci,
        uis.email: email
    }
    

    #=================BEGIN SCRIPT===========================
    try:
        arcpy.Delete_management(arcpy.env.scratchGDB) # ensures a new, fresh scratch GDB is created to avoid any weird file-not-found errors
        print("Deleted arcpy scratch GDB to ensure reliability.")
    except:
        pass


    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_vmt_report_artexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


