"""
Name: run_title_guidepg.py
Purpose: Makes title and user notice pages.


Author: Darren Conly
Last Updated: Oct 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
    

import os
from uuid import uuid4
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import datetime as dt
import json

import arcpy
arcpy.env.overwriteOutput = True
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params
import commtype
from utils import utils, make_map_img


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


def make_title_guidepg_regpgm(input_dict):

    uis = params.user_inputs
    project_fc = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    
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
    img_obj = make_map_img.MakeMapImage(project_fc, 'CoverPage', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Image Url"] = map_img_path


    # get shape of project 
    proj_shape = get_geom(project_fc)

    # generate project unique ID to enable table joining
    project_uid = str(uuid4())
    loaded_json["Project Unique ID"] = project_uid

    # write to applicable log table

    # these dict key names must match field names for master log table
    # {field name in master log table: value going in that field}
    data_to_log = {
                params.logtbl_join_key: project_uid, 
                "SHAPE@": proj_shape, 
                "comm_type": project_commtype, 
                "len_mi": tot_len_mi,
                "proj_name": project_name,
                "proj_type": input_dict[uis.ptype],
                "perf_outcomes": input_dict[uis.perf_outcomes],
                "juris": input_dict[uis.jur],
                "aadt": input_dict[uis.aadt],
                "posted_speed": input_dict[uis.posted_spd],
                "pci": input_dict[uis.pci],
                "user_email": input_dict[uis.email],
                "time_created": str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                }

    utils.log_row_to_table(data_to_log, os.path.join(params.log_fgdb, params.log_master))
 
    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"RPCoverPg{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

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
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\X_St_Oneway'
    # project_name = 'test no ctype intersect'
    # jurisdiction = 'Caltrans'
    # project_type = 'Arterial or Transit Expansion'
    # perf_outcomes = 'TEST;Reduce Congestion;Reduce VMT'
    # aadt = 150000
    # posted_spd = 65
    # pci = 80
    # email = 'fake@test.com'

    if project_type == params.ptype_commdesign:
        aadt = None
        posted_spd = None
        pci = None

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
    result_path = make_title_guidepg_regpgm(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


