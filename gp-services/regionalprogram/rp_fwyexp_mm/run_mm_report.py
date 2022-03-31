"""
Name: run_mm_report.py
Purpose: Run encourage-multimodal-travel subreport for freeway expansion projects


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
import pandas as pd
import arcpy


import parameters as params
import link_occup_data


def make_mm_report_fwyexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Freeway}_Multimodal_sample_dataSource.json")
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # calculate weekday transit trips and avg vehicle occupancy
    for i, year in enumerate(sorted(data_years)):
        fc_links_yr = params.model_links_fc(year)
        out_dict = link_occup_data.get_linkoccup_data(fc_project=fc_project, 
                                project_type=project_type,fc_model_links=fc_links_yr)

        proj_trantrips = out_dict["avg_2way_trantrips"]
        cname_trantrp = "Weekday Transit Trips"
    
        # update transit trips values
        loaded_json[params.k_charts][cname_trantrp][params.k_features][i] \
            [params.k_attrs][params.k_year] = year
        loaded_json[params.k_charts][cname_trantrp][params.k_features][i] \
            [params.k_attrs][params.k_value] =  proj_trantrips



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
    project_fc = arcpy.GetParameterAsText(0)  
    project_name = arcpy.GetParameterAsText(1) # NOTE = IS HAVING A PROJECT NAME EVEN NEEDED FOR MOST OF THESE GP TASKS?

    # hard-coded vals for testing
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBiz80curve' 
    # project_name = 'Biz80Cuve'

    ptype = params.ptype_fwy
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_mm_report_fwyexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


