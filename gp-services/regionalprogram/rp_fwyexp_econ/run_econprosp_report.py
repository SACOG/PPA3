"""
Name: run_econprosp_report.py
Purpose: Run economic prosperity subreport for freeway expansion projects


Author: Darren Conly
Last Updated: Mar 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import datetime as dt
import json
import arcpy


import parameters as params
import commtype
import chart_access_xctyp as acc_chart
import utils.make_map_img as imgmaker


def make_econ_report_fwyexp(project_fc, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Freeway}_EconProsperity_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)


    # access to jobs chart update

    chart_info_dict = {"Access to jobs": 'AUTODESTSalljob',
                        "Education Facility": 'AUTODESTSedu'}

    for chart_name, k_accdest_val in chart_info_dict.items():
        acc_chart.update_json(json_loaded=loaded_json, fc_project=project_fc, fc_accdata=params.accdata_fc,
                            proj_type=project_type, project_commtype=project_commtype, 
                            k_mode_dest=k_accdest_val, chart_title=chart_name, aggval_csv=params.aggval_csv)

    # chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
    #                                 project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
    #                                 k_chart_title="Access to jobs", destination_type='alljob')

    # # access to edu facilities chart update
    # chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
    #                                 project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
    #                                 k_chart_title="Education Facility", destination_type='edu')

    # make job accessibility map
    img_obj = imgmaker.MakeMapImage(project_fc, 'JobAccDrive', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Jobs Access by Car Image Url"] = map_img_path


    # make edu facility accessibility map
    img_obj = imgmaker.MakeMapImage(project_fc, 'EduAccDrive', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Education Access by Car Image Url"] = map_img_path

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"EconProspRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    # project_fc = arcpy.GetParameterAsText(0)  
    # project_name = arcpy.GetParameterAsText(1) 

    # test values hard coded
    project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBiz80curve'
    project_name = 'Biz80'

    ptype = params.ptype_fwy
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_econ_report_fwyexp(project_fc=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


