"""
Name: run_cd_natresource_rpt.py
Purpose: Natural resource assets subreport for community design projects


Author: Darren Conly
Last Updated: Apr 2022
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
import urbanization_metrics as urbmet
import parcel_data
import utils.utils as utils

def cd_natresource_rpt(input_dict):

    uis = params.user_inputs
    project_fc = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    ptype = input_dict[uis.ptype]


    # sometimes the scratch gdb folder becomes just a folder, so need to re-create to ensure no errors
    if arcpy.Exists(arcpy.env.scratchGDB): arcpy.Delete_management(arcpy.env.scratchGDB)
    data_years = [2016, 2040]
    lu_buffdist_ft = params.buff_nat_resources

    in_json = os.path.join(params.json_templates_dir, "SACOG_{Community Design Program}_{CommDesign}_NaturePreservation_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_poly_fc_yr(year)
        pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=project_fc,
                            buffdist=lu_buffdist_ft, project_type=ptype, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calculate change in acres of natural resources 
    k_chartname = "Change in Total Natural Resource Acres"
    acre_data_dict = {}
    for i, year in enumerate(data_years):
        fc_pcl_poly = parcel_fc_dict[year]
        nat_rsrc_dict = urbmet.nat_resources(fc_project=project_fc, projtyp=ptype, fc_pcl_poly=fc_pcl_poly)
        nat_rsrc_ac = [v for k, v in nat_rsrc_dict.items()][0]
        loaded_json[params.k_charts][k_chartname][params.k_features][i][params.k_attrs][params.k_year] = str(year)
        loaded_json[params.k_charts][k_chartname][params.k_features][i][params.k_attrs][params.k_value] = nat_rsrc_ac
        acre_data_dict[year] = nat_rsrc_ac

    nat_rsrc_ac_base = acre_data_dict[data_years[0]]
    nat_rsrc_ac_future = acre_data_dict[data_years[1]]

    # log results to data tables
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    data_to_log = {
        'project_uid': project_uid, 'ac_natlands_base': nat_rsrc_ac_base,
        'ac_natlands_fut': nat_rsrc_ac_future
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'cd_naturpres'))

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CDNatResources{project_name}{output_sufx}.json"

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
    project_type = params.ptype_commdesign
    perf_outcomes = '' # comm design projects don't choose specific perf outcomes
    aadt = None
    posted_spd = None
    pci = None
    email = arcpy.GetParameterAsText(3)

    # hard-coded vals for testing
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBroadway16th' # Broadway16th_2226
    # project_name = 'cd'
    # jurisdiction = 'cdtest'
    # project_type = params.ptype_commdesign
    # perf_outcomes = '' # comm design projects don't choose specific perf outcomes
    # aadt = None
    # posted_spd = None
    # pci = None
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
    result_path = cd_natresource_rpt(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(4, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


