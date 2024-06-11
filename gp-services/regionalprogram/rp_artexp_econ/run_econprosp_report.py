"""
Name: run_econprosp_report.py
Purpose: Run economic prosperity subreport for arterial and transit expansion projects


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
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

import parameters as params
import commtype
import parcel_data 
import landuse_buff_calcs 
import chart_accessibility
import chart_lu_acre_change
from utils import utils as utils


def convert_acc_fnames(in_dict):
    d_modenames = {'WALKDESTS': 'acc_walk', 'BIKEDESTS': 'acc_bike', 
                    'AUTODESTS': 'acc_drive', 'TRANDESTS': 'acc_transit'}

    splitter_text = 'DESTS'

    out_dict = {}
    for k, v in in_dict.items():
        
        mode_name = f"{k.split(splitter_text)[0]}{splitter_text}"
        dest_name = k.split(splitter_text)[1]
        mode_name_new = d_modenames[mode_name]

        out_field_name = f"{mode_name_new}_{dest_name}"

        out_dict[out_field_name] = v

    return out_dict


def make_econ_report_artexp(input_dict):

    uis = params.user_inputs
    fc_project=input_dict[uis.geom]
    project_name=input_dict[uis.name]
    project_type=input_dict[uis.ptype]
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_EconProsperity_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc K-12 enrollment in base year
    base_buff_pcl_fc = parcel_fc_dict[data_years[0]]
    year_dict = landuse_buff_calcs.LandUseBuffCalcs(base_buff_pcl_fc, fc_project, project_commtype, [params.col_k12_enr], 
                buffered_pcls=True).point_sum()
    k12_enr_val = year_dict[params.col_k12_enr]
    loaded_json["K12 Enrollment"] = k12_enr_val


    # calc increase in jobs between base and future year
    out_job_data = []

    for i, year in enumerate(data_years):
        in_pcl_pt_fc = parcel_fc_dict[year] # use parcels within buffer, not entire region of parcels
        year_dict = landuse_buff_calcs.LandUseBuffCalcs(in_pcl_pt_fc, fc_project, project_commtype, [params.col_emptot], 
                    buffered_pcls=True).point_sum()
        out_job_data.append(year_dict[params.col_emptot])

    job_change = out_job_data[-1] - out_job_data[0]
    loaded_json["Total new jobs added"] = job_change

    # calc change in ag acreage
    d_ag_acres = {}
    for i, year in enumerate(data_years):
        arcpy.AddMessage(f"calculating Ag land use acres for {year}")
        in_pcl_poly_fc = params.parcel_poly_fc_yr(year)
        ag_ac_yr = chart_lu_acre_change.update_json(json_loaded=loaded_json, data_year=year, order_val=i, fc_poly_parcels=in_pcl_poly_fc,
                                        project_fc=fc_project, project_type=project_type, in_lu_type='Agriculture',
                                        k_chart_title="Change in Ag acreage")
        
        d_ag_acres[year] = list(ag_ac_yr.values())[0]

    agac_base = d_ag_acres[data_years[0]]
    agac_future = d_ag_acres[data_years[1]]

    # access to jobs chart update
    acc_data_jobs = chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
                                    project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
                                    k_chart_title="Access to jobs", destination_type='alljob')

    # access to edu facilities chart update
    acc_data_edu = chart_accessibility.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
                                    project_commtype=project_commtype, aggval_csv=params.aggval_csv, 
                                    k_chart_title="Education Facility", destination_type='edu')

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"EconProspRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    # log to data table
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    acc_data_jobs_fmt = convert_acc_fnames(acc_data_jobs)
    acc_data_edu_fmt = convert_acc_fnames(acc_data_edu)


    data_to_log = {
        'project_uid': project_uid, 'enr_k12': k12_enr_val, 
        'jobs_added': job_change, 'agac_pct_base': agac_base,
        'agac_pct_future': agac_future
    }

    data_to_log.update(acc_data_jobs_fmt)
    data_to_log.update(acc_data_edu_fmt)

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artexp_econ'))

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
    # aadt = 150000
    # posted_spd = 65
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
    result_path = make_econ_report_artexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


