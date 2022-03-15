"""
Name: run_title_guidepg.py
Purpose: Freight perf subreport for arterial or transit expansion projects


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
import commtype
import utils.make_map_img as imgmaker


def make_title_guidepg_regpgm(project_name, project_fc):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Title_and_Guide_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # calculate total project length
    # NOTE 3/15/2022: on a test project on Jefferson Bl between Lake Washington and Linden,
        # Arc Pro's measuring tool says it's 0.25mi, but this script estiamtes same line to be
        # 0.19mi. As a test, daftlogic.com's distance calculator said distance is also 0.19mi.
    tot_len_ft = 0
    sr_sacog = arcpy.SpatialReference(params.projexn_wkid_sacog)
    with arcpy.da.SearchCursor(project_fc, 'SHAPE@LENGTH', spatial_reference=sr_sacog) as cur:
        for row in cur:
            seglen = row[0]
            tot_len_ft += seglen

    
    tot_len_mi = tot_len_ft / params.ft2mile

    loaded_json["Project Length Centerline Miles"] = tot_len_mi

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)
    loaded_json["Project Community Type"] = project_commtype

    # insert project map
    img_obj = imgmaker.MakeMapImage(project_fc, 'CoverPage', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Image Url"] = map_img_path


    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"RPCoverPg{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    proj_line = arcpy.GetParameterAsText(0)
    proj_name = arcpy.GetParameterAsText(1)

    # hard values for testing
    # proj_line = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestJefferson'
    # proj_name = "TestSGR"

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_title_guidepg_regpgm(project_name=proj_name, project_fc=proj_line)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


