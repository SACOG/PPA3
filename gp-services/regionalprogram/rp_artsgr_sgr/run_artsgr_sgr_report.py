"""
Name: run_artsgr_sgr_report.py
Purpose: State-of-good-repair subreport for arterial or transit state-of-good repair projects


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
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params
import complete_street_score as cs
import utils.utils as utils

# def make_sgr_report_artsgr(proj_fc, project_pci, proj_aadt, proj_postedspd, proj_typ):
def make_sgr_report_artsgr(input_dict):

    uis = params.user_inputs
    proj_fc = input_dict[uis.geom]
    proj_typ = input_dict[uis.ptype]
    project_pci = input_dict[uis.pci]
    proj_postedspd = int(input_dict[uis.posted_spd])
    proj_aadt = input_dict[uis.aadt]

    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_SGR}_SGR_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get ADT and PCI as pass-through arguments from user
    loaded_json["Pavement Condition Index"] = project_pci
    loaded_json["ADT"] = proj_aadt

    # get complete streets index value
    pcl_pts = params.parcel_pt_fc_yr(2016)
    transit_data = params.trn_svc_fc

    if proj_postedspd == 0:
        csi = -1 # don't comput CSI if user doesn't enter speed
    else:
        cs_outdict = cs.complete_streets_idx(fc_pclpt=pcl_pts, fc_project=proj_fc, project_type=proj_typ, 
                                            posted_speedlim=proj_postedspd, transit_event_fc=transit_data)

        csi = cs_outdict['complete_street_score'] / params.cs_region_max * 100

    loaded_json["Complete Streets Index"] = csi

    # log to data table
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    data_to_log = {
        'project_uid': project_uid, 'pci': project_pci, 
        'aadt': proj_aadt, 'cs_index': csi
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artsgr_sgr'))

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"SGRRpt{output_sufx}.json"

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
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBroadway16th' # Broadway16th_2226
    # project_name = 'broadway'
    # jurisdiction = 'sac city' 
    # project_type = params.ptype_arterial
    # perf_outcomes = 'TEST;Reduce Congestion;Reduce VMT'
    # aadt = 22000
    # posted_spd = 30
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
    result_path = make_sgr_report_artsgr(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


