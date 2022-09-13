"""
Name: use_json_in.py
Purpose: 
    TESTING script to see if following will work:
    * Script takes in a JSON file as an input
    * Can retrieve spatial and non-spatial data

Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import json

import arcpy

def do_work(in_json):
    line_json = in_json["Project_Line"]
    name = in_json["Project_Name"]
    email = in_json["userEmail"]

    proj_len = 0

    import pdb;pdb.set_trace()
    temp_fc = os.path.join(arcpy.env.scratchGDB,"TEMP_from_JSON")
    arcpy.JSONToFeatures_conversion(line_json, temp_fc)

    with arcpy.da.SearchCursor(temp_fc, "SHAPE@LENGTH") as cur:
        for row in cur:
            proj_len += row[0]


    out_msg = f"""
    Name: {name}
    Email: {email}
    Length: {proj_len}
    """

    arcpy.AddMessage(out_msg)

if __name__ == '__main__':
    project_fc = arcpy.GetParameterAsText(0)
    input_json = arcpy.GetParameterAsText(1)


    input_json = r"C:\Users\dconly\GitRepos\PPA3\vertigis-deliverables\input_json_samples\gp_inputs_ex1.json"
    project_json = r"I:\Projects\Darren\PPA3_GIS\JSON\x_street_export_from_fc.json"
    
    with open(input_json, 'r') as j:
        json_projdata = json.load(j)

    with open(project_json, 'r') as j:
        json_projgeom = json.load(j)

    json_projdata['Project_Line'] = json_projgeom

    # import pdb; pdb.set_trace()

    do_work(json_projdata)