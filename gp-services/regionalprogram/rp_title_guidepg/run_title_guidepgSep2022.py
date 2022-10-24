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
import pickle
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder
# sys.path.append("utils") # attempting this so that the utils folder will copy to server during publishing (3/11/2022)

import datetime as dt
import json

import arcpy
arcpy.env.overwriteOutput = True

import parameters as params
import commtype
import utils.make_map_img as imgmaker
import utils.utils as utils

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


    #==========STUFF FOR POTENTIALLY LOGGING TO FGDB; COMMENT OUT FOR NOW
    # # get shape of project 
    # proj_shape = get_geom(project_fc)

    # # write to applicable log table
    # data_to_log = {"SHAPE@": proj_shape, "comm_type": project_commtype, 
    #             "len_mi": tot_len_mi}
    # project_uid = utils.log_row_to_table(data_to_log, os.path.join(params.log_fgdb, params.log_master))
    
    # # use the new OBJECTID generated as the lookup key between master and subreport tables.
    # with open(params.pickle_uid, 'wb') as f: pickle.dump(project_uid)

    # with open(out_file, 'w') as f_out:
    #     json.dump(loaded_json, f_out, indent=4)

    # --------------write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"RPCoverPg{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    proj_line = arcpy.GetParameterAsText(0)
    proj_name = arcpy.GetParameterAsText(1)

    # hard values for testing
    # proj_line = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\JStreetWGS84_multiFeature'
    # proj_name = "TestSGR"

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_title_guidepg_regpgm(project_name=proj_name, project_fc=proj_line)

    import pdb; pdb.set_trace()

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")

