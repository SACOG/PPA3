"""
Name: run_equity_report.py
Purpose: Run equity subreport for arterial and transit expansion projects


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
import chart_accessibility_projonly as chart_acc
import get_agg_values as aggvals
import utils.utils as utils


def update_tbl_multiple_geos(json_obj, proj_level_val, k_chartname_metric, metric_outdictkey, proj_commtype):
    """Updates project-level, community-type, and region-level values for simple tables in JSON file."
    """

    ixn_aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[metric_outdictkey], 
                                                proj_ctype=proj_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    val_ctyp = ixn_aggdict[metric_outdictkey][proj_commtype]
    val_regn = ixn_aggdict[metric_outdictkey][params.geo_region]

    json_obj[k_chartname_metric]["Within project location"] = proj_level_val
    json_obj[k_chartname_metric]["Within community type"] = val_ctyp
    json_obj[k_chartname_metric]["Within region"] = val_regn


def make_equity_rpt_artexp(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype]  
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Equity_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016]

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


    # Get data on population living in EJ areas
    base_buff_pcl_fc = parcel_fc_dict[data_years[0]]
    year_dict = landuse_buff_calcs.LandUseBuffCalcs(base_buff_pcl_fc, fc_project, project_commtype, [params.col_pop_ilut], 
                buffered_pcls=True, case_field=params.col_ej_ind).point_sum()


    pop_non_ej = 0 if year_dict.get(0) is None else year_dict.get(0) # must use get() in case key is not in dict
    pop_ej = 0 if year_dict.get(1) is None else year_dict.get(1)

    pop_tot = pop_non_ej + pop_ej

    project_pct_ej = pop_ej / pop_tot if pop_tot > 0 else 0

    k_chartname = "Share of population living in EJ community"
    k_metric = 'Pct_PopEJArea'
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=project_pct_ej, k_chartname_metric=k_chartname,
                            metric_outdictkey=k_metric, proj_commtype=project_commtype)

    
    # update total EJ population -- NOTE that the JSON tag should be changed from "Population" to "EJ Population"
    loaded_json["Population"] = pop_ej

    # access to jobs chart update
    d_acc = chart_acc.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
                                    k_chart_title="Total Job Accessibility", destination_type='alljob_EJ', 
                                    get_ej_only=True)

    # access to edu facilities chart update
    d_eduacc = chart_acc.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type, 
                                    k_chart_title="Education Accessibility", destination_type='edu_EJ', 
                                    get_ej_only=True)

    # access to services chart update
    d_svcacc = chart_acc.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type, 
                                    k_chart_title="Services Accessibility", destination_type='poi2_EJ', 
                                    get_ej_only=True)

    # log to data table
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    acc_walk_alljob_ej = d_acc[f"{params.col_walk_alljob}_EJ"]
    acc_bike_alljob_ej = d_acc[f"{params.col_bike_alljob}_EJ"]
    acc_drive_alljob_ej = d_acc[f"{params.col_drive_alljob}_EJ"]
    acc_transit_alljob_ej = d_acc[f"{params.col_transit_alljob}_EJ"]

    data_to_log = {
        'project_uid': project_uid, 
        'pop_tot': pop_tot, 'pop_ej_area': pop_ej,
        'pctpot_ej_area': project_pct_ej, 'acc_walk_alljob_ej': acc_walk_alljob_ej,
        'acc_bike_alljob_ej': acc_bike_alljob_ej, 'acc_drive_alljob_ej': acc_drive_alljob_ej,
        'acc_transit_alljob_ej': acc_transit_alljob_ej
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artexp_eq'))


    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"EquityRpt{project_name}{output_sufx}.json"

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
    result_path = make_equity_rpt_artexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


