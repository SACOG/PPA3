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
from uuid import uuid4
import pickle
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder
# sys.path.append("utils") # attempting this so that the utils folder will copy to server during publishing (3/11/2022)

import datetime as dt
import json

import arcpy
arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False)

import parameters as params
# from parameters import json_templates_dir, projexn_wkid_sacog, comm_types_fc, ft2mile, pickle_uid, logtbl_join_key, log_fgdb, log_master, ptype_arterial, fgdb
import commtype
import utils.make_map_img as imgmaker
# import utils.utils as utils

def log_row_to_table(data_row_dict, dest_table):
    """Writes row of values to table. Fields are data_row_dict keys, and the values
    written are the values from data_row_dict's values."""

    data_fields = list(data_row_dict.keys())
    data_values = list(data_row_dict.values())

    with arcpy.da.InsertCursor(dest_table, data_fields) as cur:
        cur.insertRow(data_values)

    arcpy.AddMessage(f"Logged subreport values to {dest_table}")

def get_geom(in_fc):
    """Get the geometry object from input feature class.
    If in_fc has multiple features, it's first dissolved and the returned
    geometry is that of the dissolved feature class."""

    if int(arcpy.GetCount_management(in_fc)[0]) > 1:
        in_fc_diss = os.path.join(arcpy.env.scratchGDB, "input_fc_dissolved")
        arcpy.Dissolve_management(in_fc, in_fc_diss)
        in_fc = in_fc_diss

    with arcpy.da.SearchCursor(in_fc, ["SHAPE@"]) as scur:
        for row in scur:
            output_geom = row[0]

    return output_geom

def parse_project_json(input_json):
    with open(input_json, 'r') as j:
        project_info_dict = json.load(j)
    
    js_geom = json.dumps(project_info_dict['Project_Line'])
    fs_project_line = arcpy.FeatureSet(js_geom)

    return (fs_project_line, project_info_dict)

def make_title_guidepg_regpgm(project_json):

    project_data = parse_project_json(project_json)
    project_fc = project_data[0]
    project_info = project_data[1]

    project_name = project_info['Project_Name']
    
    rpt_template_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Title_and_Guide_sample_dataSource.json")

    with open(rpt_template_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # calculate total project length
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


    # get shape of project 
    proj_shape = get_geom(project_fc)

    # write to applicable log table
    # use the new OBJECTID generated as the lookup key between master and subreport tables.
    project_uid = str(uuid4())
    with open(params.pickle_uid, 'wb') as f: pickle.dump(project_uid, f)

    data_to_log = {params.logtbl_join_key:project_uid, "SHAPE@":proj_shape, 
                    "comm_type":project_commtype, "len_mi": tot_len_mi}

    log_row_to_table(data_to_log, os.path.join(params.log_fgdb, params.log_master))
 
    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"RPCoverPg{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file

    """
    log_row_to_table(input_json, dest_table)
    """


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============
    in_json = arcpy.GetParameterAsText(0)

    # in_json = r"C:\Users\dconly\GitRepos\PPA3\vertigis-deliverables\input_json_samples\gp_inputs_ex1.json"

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    try:
        arcpy.Delete_management(arcpy.env.scratchGDB) # ensures a new, fresh scratch GDB is created to avoid any weird file-not-found errors
        print("Deleted arcpy scratch GDB to ensure reliability.")
    except:
        pass


    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_title_guidepg_regpgm(project_json=in_json)

    arcpy.SetParameterAsText(1, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


