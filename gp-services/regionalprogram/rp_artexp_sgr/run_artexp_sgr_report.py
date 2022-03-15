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
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder
# sys.path.append("utils") # attempting this so that the utils folder will copy to server during publishing (3/11/2022)

import datetime as dt
import json

import arcpy

import parameters as params


def make_sgr_report_artexp(project_pci, project_name, proj_aadt):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_SGR_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    loaded_json["Pavement Condition Index"] = project_pci
    loaded_json["ADT"] = proj_aadt

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"SGRRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    proj_name = arcpy.GetParameterAsText(0)
    proj_pci = int(arcpy.GetParameterAsText(1))
    proj_aadt = int(arcpy.GetParameterAsText(2))  

    # hard values for testing
    # proj_pci = 67
    # proj_name = "TestSGR"
    # proj_aadt = 13500

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_sgr_report_artexp(project_pci=proj_pci,project_name=proj_name , proj_aadt=proj_aadt)

    arcpy.SetParameterAsText(3, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


