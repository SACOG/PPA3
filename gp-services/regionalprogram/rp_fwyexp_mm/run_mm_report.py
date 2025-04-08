"""
Name: run_vmt_report.py
Purpose: Run reduce-VMT subreport for freeway expansion projects


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

from config_links import params
import link_occup_data
from utils import utils as utils


# def make_vmt_report_fwyexp(fc_project, project_name, project_type):
def make_mm_report_fwyexp(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype] 
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Freeway}_Multimodal_sample_dataSource.json")
    data_years = [params.base_year, params.future_year]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # calculate weekday transit trips and avg vehicle occupancy
    output_data = {}
    for i, year in enumerate(sorted(data_years)):
        fc_links_yr = params.model_links_fc(year)
        out_dict = link_occup_data.get_linkoccup_data(fc_project=fc_project, 
                                project_type=project_type,fc_model_links=fc_links_yr)

        # what the out_dict looks like: {'avg_2way_trantrips': 447.89406870675947, 'avg_2way_vehocc': 1.348670013997033}

        proj_trantrips = out_dict["avg_2way_trantrips"]
        cname_trantrp = "Weekday Transit Trips"
    
        # update transit trips values
        loaded_json[params.k_charts][cname_trantrp][params.k_features][i] \
            [params.k_attrs][params.k_year] = str(year)
        loaded_json[params.k_charts][cname_trantrp][params.k_features][i] \
            [params.k_attrs][params.k_value] = proj_trantrips

        output_data[year] = out_dict
    # resulting output dict = {2016:{trantrips:val, vehocc:val}, 2040:{trantrips:val, vehocc:val}}

    # log to data table
    project_uid = utils.get_project_uid(input_dict)

    base_trntrip = output_data[data_years[0]]['avg_2way_trantrips']
    future_trntrip = output_data[data_years[1]]['avg_2way_trantrips']

    data_to_log = {
        'project_uid': project_uid, 'base_trntrip': base_trntrip,
        'future_trntrip': future_trntrip
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_fwy_mm'))

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
    project_fc = arcpy.GetParameterAsText(0)
    project_name = arcpy.GetParameterAsText(1)
    jurisdiction = arcpy.GetParameterAsText(2)
    project_type = arcpy.GetParameterAsText(3)
    perf_outcomes = arcpy.GetParameterAsText(4)
    aadt = arcpy.GetParameterAsText(5)
    posted_spd = arcpy.GetParameterAsText(6)
    pci = arcpy.GetParameterAsText(7)
    email = arcpy.GetParameterAsText(8)

    # hard-coded vals for testing
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_I5SMF' # Broadway16th_2226
    # project_name = 'causeway'
    # jurisdiction = 'caltrans'
    # project_type = params.ptype_fwy
    # perf_outcomes = 'TEST;Reduce Congestion;Reduce VMT'
    # aadt = 150000
    # posted_spd = 65
    # pci = 80
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
    result_path = make_mm_report_fwyexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


