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

def do_work(in_json, in_fc):
    name = in_json["Project_Name"]
    email = in_json["userEmail"]

    proj_len = 0
    with arcpy.da.SearchCursor(in_fc, "SHAPE@LENGTH") as cur:
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


    # input_json = r"C:\Users\dconly\GitRepos\PPA3\vertigis-deliverables\input_json_samples\gp_inputs_ex1.json"
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBroadway16th'
    
    with open(input_json, 'r') as j:
        json_loaded = json.load(j)


    do_work(json_loaded, project_fc)