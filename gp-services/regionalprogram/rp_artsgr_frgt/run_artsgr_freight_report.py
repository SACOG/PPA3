"""
Name: run_artexp_freight_report.py
Purpose: Freight perf subreport for arterial SGR projects


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
import parcel_data 
import landuse_buff_calcs 
import get_line_overlap as glo
import get_agg_values as aggvals
import utils.make_map_img as imgmaker


def pct_jobs_sector_year(parcel_pt_file, col_emptot, col_empsector):
    # calculates percent of jobs in sector for specified parcel file
    out_dict = landuse_buff_calcs.LandUseBuffCalcs(parcel_pt_file, fc_project=None, 
            project_type=None, val_fields=[col_empsector, col_emptot], buffered_pcls=True).point_sum()

    if out_dict[col_emptot] == 0:
        pct_jobs_sector = 0
    else:
        pct_jobs_sector = out_dict[col_empsector] / out_dict[col_emptot]
        
    return pct_jobs_sector


def make_econ_report_artexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_SGR}_Freight_sample_dataSource.json")
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

    
    # calculate share of project miles that are on an STAA truck route
    link_desc = "STAATruckRte"
    staa_overlap_dict = glo.get_line_overlap(fc_project, params.freight_route_fc, link_desc)
    staa_pct = staa_overlap_dict[f'pct_proj_{link_desc}']
    loaded_json["Percent Project on STAA"] = staa_pct


    # generate map image of STAA truck routes and insert link to image
    
    img_obj = imgmaker.MakeMapImage(fc_project, 'TruckRtes', project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["STAA network Image Url"] = map_img_path


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
    project_fc = arcpy.GetParameterAsText(0)  # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'
    project_name = arcpy.GetParameterAsText(1)  # 'TestTruxelBridge'

    # hard values for testing
    # project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\PPAClientRun_StocktonBlCS'
    # project_name = 'StocktonCS'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_econ_report_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


