"""
Name: run_cd_existassets_rpt.py
Purpose: Existing assets subreport for community design projects


Author: Darren Conly
Last Updated: Apr 2022
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
import commtype
import chart_accessibility
import urbanization_metrics as urbmet


def cd_existassets_rpt(fc_project, project_name, project_type):
    # sometimes the scratch gdb folder becomes just a folder, so need to re-create to ensure no errors
    if arcpy.Exists(arcpy.env.scratchGDB): arcpy.Delete_management(arcpy.env.scratchGDB)

    in_json = os.path.join(params.json_templates_dir, "SACOG_{Community Design Program}_{CommDesign}_ExistingAssets_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)    

    # get service accessibility numbers
    chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=ptype,
                                    project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
                                    k_chart_title="Accessibility to Services")      

    # Tag if project is in an infill or greenfield area                          
    k_status = "Project location infill status"
    urban_status_dict = urbmet.projarea_infill_status(fc_project=project_fc, comm_types_fc=params.comm_types_fc)

    urban_status = [v for k, v in urban_status_dict.items()][0]

    loaded_json[k_status] = urban_status

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CDExistAssets{project_name}{output_sufx}.json"

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
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestJefferson'
    # project_name = 'TestJefferson'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = cd_existassets_rpt(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


