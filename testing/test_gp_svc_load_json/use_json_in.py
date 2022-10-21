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
import parameters_useyaml as params
import utils.make_map_img as imgmaker
arcpy.AddMessage('imported make_map_img.py from utils folder')
# arcpy.AddMessage("imported params.py successfully")

def do_work(in_json):
    name = in_json["Project_Name"]
    email = in_json["userEmail"]


    out_msg = f"""
    Name: {name}
    Email: {email}
    Project Line Template Name from Param File: {params.proj_line_template_fc}
    """

    arcpy.AddMessage(out_msg)

if __name__ == '__main__':
    input_json = arcpy.GetParameterAsText(0)
    # input_json = r"C:\Users\dconly\GitRepos\PPA3\vertigis-deliverables\input_json_samples\gp_inputs_ex1.json"


    
    with open(input_json, 'r') as j:
        json_loaded = json.load(j)


    do_work(json_loaded)