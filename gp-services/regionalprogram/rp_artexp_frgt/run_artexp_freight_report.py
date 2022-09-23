"""
Name: run_artexp_freight_report.py
Purpose: Freight perf subreport for arterial or transit expansion projects


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
import get_line_overlap as glo
import get_agg_values as aggvals
import utils.make_map_img as imgmaker
import utils.utils as utils


def pct_jobs_sector_year(parcel_pt_file, col_emptot, col_empsector):
    # calculates percent of jobs in sector for specified parcel file
    out_dict = landuse_buff_calcs.LandUseBuffCalcs(parcel_pt_file, fc_project=None, 
            project_type=None, val_fields=[col_empsector, col_emptot], buffered_pcls=True).point_sum()

    if out_dict[col_emptot] == 0:
        pct_jobs_sector = 0
    else:
        pct_jobs_sector = out_dict[col_empsector] / out_dict[col_emptot]
        
    return pct_jobs_sector


def make_frgt_report_artexp(project_json, project_type):

    project_data = utils.parse_project_json(project_json)
    fc_project = project_data[0]
    project_info = project_data[1]
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Freight_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(fc_project, params.comm_types_fc)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc percent of jobs in industrial sectors in base year for project,
    # community type, and region (use columns params.col_empind, params.col_emptot)
    k_tbl_name = "Share of jobs in industrial sectors"
    base_buff_pcl_fc = parcel_fc_dict[data_years[0]]
    pct_ind_jobs_project = pct_jobs_sector_year(base_buff_pcl_fc, params.col_emptot, params.col_empind)

    empind_jshare_col = f"{params.col_empind}_jobshare"
    indjobs_aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[empind_jshare_col], 
                                                proj_ctype=project_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    pct_ind_jobs_ctype = indjobs_aggdict[empind_jshare_col][project_commtype]
    pct_ind_jobs_regn = indjobs_aggdict[empind_jshare_col][params.geo_region]

    loaded_json[k_tbl_name]["Within 0.5mi of project"] = pct_ind_jobs_project
    loaded_json[k_tbl_name]["Within community type"] = pct_ind_jobs_ctype
    loaded_json[k_tbl_name]["Within region"] = pct_ind_jobs_regn


    # calc change in share of jobs that are in industrial sectors
    k_chart_title = "Change in share of industrial jobs"
    for i, year in enumerate(data_years):
        arcpy.AddMessage(f"calculating Ag land use acres for {year}")
        in_pcl_pt_fc = parcel_fc_dict[year]
        pct_ind_jobs = pct_jobs_sector_year(in_pcl_pt_fc, params.col_emptot, params.col_empind)

        loaded_json[params.k_charts][k_chart_title][params.k_features][i][params.k_attrs][params.k_year] = str(year) # need to convert to string for chart
        loaded_json[params.k_charts][k_chart_title][params.k_features][i][params.k_attrs][params.k_value] = pct_ind_jobs

    
    # calculate share of project miles that are on an STAA truck route
    link_desc = "STAATruckRte"
    staa_overlap_dict = glo.get_line_overlap(fc_project, params.freight_route_fc, link_desc)
    staa_pct = staa_overlap_dict[f'pct_proj_{link_desc}']
    loaded_json["Percent Project on STAA"] = staa_pct


    # generate map image of STAA truck routes and insert link to image
    
    project_name = project_info[params.user_inputs.name]
    img_obj = imgmaker.MakeMapImage(fc_project, 'TruckRtes', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["STAA network Image Url"] = map_img_path

    # log results to archive table
    # INSERT CODE HERE


    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"FreightRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    json_in = arcpy.GetParameterAsText(0) 
    
    

    # hard values for testing
    # json_in = r"C:\Users\dconly\GitRepos\PPA3\vertigis-deliverables\input_json_samples\gp_inputs_ex1.json"

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_frgt_report_artexp(project_json=json_in, project_type=ptype)

    arcpy.SetParameterAsText(1, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


