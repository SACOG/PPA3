"""
Name: run_compactdev_report.py
Purpose: calculate numbers for the community design "compact development" subreport and produce applicable charts.


Author: Darren Conly
Last Updated: Apr 2022
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
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params
import parcel_data
import chart_job_du_tot
import utils.utils as utils


def cd_compactdev_rpt(input_dict):
    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype] 

    in_json = os.path.join(params.json_templates_dir, "SACOG_{Community Design Program}_{CommDesign}_CompactDev_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc


    # calc land use buffer values 
    d_lubuff = {}
    for i, year in enumerate(data_years):
        in_pcl_pt_fc = parcel_fc_dict[year]
        d_jobdu = chart_job_du_tot.update_json(json_loaded=loaded_json, data_year=year, order_val=i, pcl_pt_fc=in_pcl_pt_fc, 
                                    project_fc=project_fc, project_type=project_type)

        # {f"jobs": jobs, f"dwellingUnits": du}
        d_lubuff[year] = d_jobdu
    
    job_base = d_lubuff[data_years[0]]["jobs"]
    job_future = d_lubuff[data_years[1]]["jobs"]
    du_base = d_lubuff[data_years[0]]["dwellingUnits"]
    du_future = d_lubuff[data_years[1]]["dwellingUnits"]

    # log results to data tables
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    data_to_log = {
        'project_uid': project_uid, 'jobs_base': job_base, 
        'jobs_future': job_future, 'du_base': du_base, 
        'du_future': du_future
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'cd_compactdev'))

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CD_CompactDev{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============

    # inputs from tool interface
    project_fc = arcpy.GetParameterAsText(0)
    project_name = arcpy.GetParameterAsText(1)
    jurisdiction = arcpy.GetParameterAsText(2)
    project_type = params.ptype_commdesign
    perf_outcomes = '' # comm design projects don't choose specific perf outcomes
    aadt = None
    posted_spd = None
    pci = None
    email = arcpy.GetParameterAsText(3)

    # hard-coded vals for testing
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBroadway16th' # Broadway16th_2226
    # project_name = 'cd'
    # jurisdiction = 'cdtest'
    # project_type = params.ptype_commdesign
    # perf_outcomes = '' # comm design projects don't choose specific perf outcomes
    # aadt = None
    # posted_spd = None
    # pci = None
    # email = 'fake@test.com'

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
    result_path = cd_compactdev_rpt(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(4, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


