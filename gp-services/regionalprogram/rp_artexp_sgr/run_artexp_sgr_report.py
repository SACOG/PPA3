"""
Name: run_artexp_sgr_report.py
Purpose: State-of-good-repair subreport for arterial or transit expansion projects


Author: Darren Conly
Last Updated: Mar 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
    

import os
import pickle
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder
# sys.path.append("utils") # attempting this so that the utils folder will copy to server during publishing (3/11/2022)

import datetime as dt
import json

import arcpy
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params


def make_sgr_report_artexp(input_dict):

    uis = params.user_inputs
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_SGR_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    loaded_json["Pavement Condition Index"] = input_dict[uis.pci]
    loaded_json["ADT"] = input_dict[uis.aadt]

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"SGRRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    # log to master table
    project_uid = pickle.load(open())

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
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_Causeway'
    # project_name = 'causeway'
    # jurisdiction = 'Caltrans'
    # project_type = 'Arterial Expansion'
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
    result_path = make_sgr_report_artexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


