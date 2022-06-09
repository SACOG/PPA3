"""
Name: run_fwy_freight_report.py
Purpose: Freight perf subreport for freeway expansion projects


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
import json
import arcpy


import parameters as params
import get_truck_data_fwy as truckdata


def make_freight_rept_fwyexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Freeway}_Freight_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    
    # calculate share of project miles that are on an STAA truck route
    loaded_json["Project on Federally Recognized STAA"] = 1.0 # All freeways in the SACOG region are STAA truck routes. 1.0 = 100%

    # calculate share of traffic volume that is trucks
    output_data = truckdata.get_tmc_truck_data(fc_projline=fc_project, str_project_type=project_type)
    truck_pct = output_data[f"{params.col_truckpct}_proj"] / 100 
    loaded_json["Share of Traffic on Segment That is Trucks"] = truck_pct

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"FreightRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)
    project_name = arcpy.GetParameterAsText(1) 

    # hard values for testing
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_I5SMF'
    # project_name = 'test'

    ptype = params.ptype_fwy
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_freight_rept_fwyexp(fc_project=project_fc, project_name=project_name,
                                        project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


