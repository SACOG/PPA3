"""
Name: run_econprosp_report.py
Purpose: Run economic prosperity subreport for freeway expansion projects


Author: Darren Conly
Last Updated: Mar 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent)) # enable importing from parent folder

import datetime as dt
import json
import arcpy
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params
import commtype
import chart_access_xctyp as acc_chart
from utils import make_map_img as imgmaker
from utils import utils as utils

def convert_acc_fnames(in_dict):
    # converts to allow writing to log table. 

    # {mode name: field name in log table that vals will write to}
    d_modenames = {'walk': 'acc_walk', 'bike': 'acc_bike', 
                    'drive': 'acc_drive', 'transit': 'acc_transit'}
    
    d_destnames = {'emp': 'alljob', 'nonwork': 'svc', 'edu': 'edu'}

    splitter_text = '_'

    out_dict = {}
    for k, v in in_dict.items():
        mode_name = k.split(splitter_text)[0]
        dest_name = k.split(splitter_text)[1]
        out_field_name = f"{d_modenames[mode_name]}_{d_destnames[dest_name]}"
        out_dict[out_field_name] = v

    return out_dict

def make_econ_report_fwyexp(input_dict):

    uis = params.user_inputs
    project_fc=input_dict[uis.geom]
    project_name=input_dict[uis.name]
    project_type=input_dict[uis.ptype]
    
    in_json = Path(params.json_templates_dir).joinpath("SACOG_{Regional Program}_{Freeway}_EconProsperity_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)


    # access to jobs and education, chart update
    chart_info_dict = {"Access to jobs": {'dest': 'emp', 'wgt': 'workers'}}

    acc_data = {}
    for chart_name, k_accdest_val in chart_info_dict.items():
        acc_data_i = acc_chart.update_json(json_loaded=loaded_json, fc_project=project_fc,
                            proj_type=project_type, project_commtype=project_commtype, weight_pop=k_accdest_val['wgt'],
                            mode='drive', dest=k_accdest_val['dest'], chart_title=chart_name, aggval_csv=params.aggval_csv)
        acc_data.update(acc_data_i)

    acc_data_fmt = convert_acc_fnames(acc_data)

    # make job accessibility map
    img_obj = imgmaker.MakeMapImage(project_fc, 'JobAccDrive', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Jobs Access by Car Image Url"] = map_img_path


    # make edu facility accessibility map
    img_obj = imgmaker.MakeMapImage(project_fc, 'EduAccDrive', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Education Access by Car Image Url"] = map_img_path

    # log to data table
    project_uid = utils.get_project_uid(input_dict)

    f_acc_drive_job = 'acc_drive_alljob'
    acc_drive_job = acc_data_fmt[f_acc_drive_job]

    data_to_log = {'project_uid': project_uid, f_acc_drive_job: acc_drive_job}

    dest_tbl = str(Path(params.log_fgdb).joinpath('rp_fwy_econ'))
    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=dest_tbl)

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"EconProspRpt{project_name}{output_sufx}.json"

    out_file = Path(output_dir).joinpath(out_file_name)
    
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
    project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_I5_NoNa' # Broadway16th_2226
    project_name = 'I5'
    jurisdiction = 'caltrans'
    project_type = params.ptype_fwy
    perf_outcomes = 'TEST;Reduce Congestion;Reduce VMT'
    aadt = 150000
    posted_spd = 65
    pci = 80
    email = 'fake@test.com'

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
    result_path = make_econ_report_fwyexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


