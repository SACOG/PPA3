"""
Name: run_cd_transpochoice_rpt.py
Purpose: Transportation choice subreport for community design projects


Author: Darren Conly
Last Updated: Mar 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
    

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder
# sys.path.append("utils") # attempting this so that the utils folder will copy to server during publishing (3/11/2022)

import datetime as dt
import json
import arcpy
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params
import parcel_data 
import chart_mode_split 
from utils import utils as utils

def convert_mode_keys(in_dict_w_sorted_years):
    # converts mode split names to match field names in the log table
    # input dict format: {year1:{mode1: mode1pct, mode2:mode2pct,...}, year2:{mode1: mode1pct, mode2:mode2pct,...}}
    
    mode_name_dict = {
        'Single-occupant vehicle': 'sovpct', 'Carpool': 'hovpct',
        'Transit': 'ptpct', 'Biking': 'bikepct',
        'Walking': 'walkpct'}

    years_for_output = ['base', 'fut']

    out_dict = {}
    for i, datavals in enumerate(in_dict_w_sorted_years.items()):
        # year = datavals.keys()[0]
        
        modesplits_dict_in = datavals[1]

        yeartag = years_for_output[i]

        for k, v in modesplits_dict_in.items():
            k_new = f"{yeartag}_{mode_name_dict[k]}"
            out_dict[k_new] = v

    return out_dict

def cd_transpochoice_rpt(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype] 
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Community Design Program}_{CommDesign}_TransportationChoice_sample_dataSource.json")
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

    mode_split_data = {}
    for i, year in enumerate(data_years):
        pcl_fc = parcel_fc_dict[year]
        mode_data_yr = chart_mode_split.update_json(json_loaded=loaded_json, data_year=year, pcl_pt_fc=pcl_fc, 
                                    project_fc=fc_project, project_type=project_type)
        
        mode_split_data[year] = mode_data_yr
        

    mode_split_data_conv = convert_mode_keys(mode_split_data)


    # log results to data tables
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    data_to_log = {
        'project_uid': project_uid
    }

    data_to_log.update(mode_split_data_conv)

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'cd_trnchoice'))
    
    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CDTranspoChoice{project_name}{output_sufx}.json"

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
    result_path = cd_transpochoice_rpt(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(4, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


