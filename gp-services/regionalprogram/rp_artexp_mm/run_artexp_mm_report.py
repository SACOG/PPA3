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


import parameters as params
import commtype
import parcel_data 
import chart_mode_split 
import intersection_density
import get_buff_netmiles
import get_agg_values as aggvals
import utils.make_map_img as imgmaker


def make_mm_report_artexp(fc_project, project_name, project_type):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Multimodal_sample_dataSource.json")
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

    # calc mode split 
    for i, year in enumerate(data_years):
        pcl_fc = parcel_fc_dict[year]
        chart_mode_split.update_json(json_loaded=loaded_json, data_year=year, order_val=i,
                                pcl_pt_fc=pcl_fc, project_fc=fc_project, project_type=project_type)


    # calculate intersections per acre
    k_chart_ixns = "Intersections per acre"
    intxn_keyval = 'Intersxn_34_per_acre'
    ixn_density_dict = intersection_density.intersection_density(fc_project, params.intersections_base_fc)
    ixn_density_project = ixn_density_dict[intxn_keyval]

    ixn_aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[intxn_keyval], 
                                                proj_ctype=project_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    ixn_commtype = ixn_aggdict[intxn_keyval][project_commtype]
    ixn_region = ixn_aggdict[intxn_keyval][params.geo_region]

    loaded_json[k_chart_ixns][params.geo_proj_qmi] = ixn_density_project
    loaded_json[k_chart_ixns][params.geo_ctype] = ixn_commtype
    loaded_json[k_chart_ixns][params.geo_region] = ixn_region

    
    # calculate share of centerline miles near project that are bike paths or streets with bike lanes
    k_chart_bkwy = "Bike lanes and paths as share of total road miles"
    bkwymi_keyval = 'pct_roadmi_bikeways'

    bkwy_proj_data = get_buff_netmiles.get_bikeway_mileage_share(fc_project, project_type)
    bkwy_proj = bkwy_proj_data[bkwymi_keyval]

    ixn_aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[bkwymi_keyval], 
                                                proj_ctype=project_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    bkwy_ctyp = ixn_aggdict[bkwymi_keyval][project_commtype]
    bkwy_regn = ixn_aggdict[bkwymi_keyval][params.geo_region]

    loaded_json[k_chart_bkwy][params.geo_proj_qmi] = bkwy_proj
    loaded_json[k_chart_bkwy][params.geo_ctype] = bkwy_ctyp
    loaded_json[k_chart_bkwy][params.geo_region] = bkwy_regn



    # generate map image of bikeway network
    
    img_obj = imgmaker.MakeMapImage(fc_project, "BikeRoutes", project_name)
    map_img_path = img_obj.exportMap()
    loaded_json["Bikeway Image Url"] = map_img_path


    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"MultiModalRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    # project_fc = arcpy.GetParameterAsText(0)  # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'
    # project_name = arcpy.GetParameterAsText(1)  # 'TestTruxelBridge'

    # hard values for testing
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\PPAClientRun_StocktonBlCS'
    project_name = 'StocktonCS'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_mm_report_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


