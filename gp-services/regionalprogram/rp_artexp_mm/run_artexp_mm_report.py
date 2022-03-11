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
# sys.path.append("utils") # attempting this so that the utils folder will copy to server during publishing (3/11/2022)

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
import transit_svc_measure
import utils.make_map_img as imgmaker

def update_tbl_multiple_geos(json_obj, proj_level_val, k_chartname_metric, metric_outdictkey, proj_commtype):
    """Updates project-level, community-type, and region-level values for simple tables in JSON file."
    """

    ixn_aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[metric_outdictkey], 
                                                proj_ctype=proj_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    val_ctyp = ixn_aggdict[metric_outdictkey][proj_commtype]
    val_regn = ixn_aggdict[metric_outdictkey][params.geo_region]

    json_obj[k_chartname_metric][params.geo_proj_qmi] = proj_level_val
    json_obj[k_chartname_metric][params.geo_ctype] = val_ctyp
    json_obj[k_chartname_metric][params.geo_region] = val_regn


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
        chart_mode_split.update_json(json_loaded=loaded_json, data_year=year, pcl_pt_fc=pcl_fc, 
                                    project_fc=fc_project, project_type=project_type)


    # calculate intersections per acre
    k_chart_ixns = "Intersections per acre"
    intxn_keyval = 'Intersxn_34_per_acre'
    ixn_density_dict = intersection_density.intersection_density(fc_project, params.intersections_base_fc, project_type)
    ixn_density_project = ixn_density_dict[intxn_keyval]

    update_tbl_multiple_geos(loaded_json, ixn_density_project, k_chart_ixns, intxn_keyval, project_commtype)

    
    # calculate share of centerline miles near project that are bike paths or streets with bike lanes
    k_chart_bkwy = "Bike lanes and paths as share of total road miles"
    bkwymi_keyval = 'pct_roadmi_bikeways'

    project_bikeway_dict = get_buff_netmiles.get_bikeway_mileage_share(fc_project, project_type)
    project_bikeway_data = project_bikeway_dict[bkwymi_keyval]
    update_tbl_multiple_geos(loaded_json, project_bikeway_data, k_chart_bkwy, bkwymi_keyval, project_commtype)


    # calculate transit vehicle-stops per acre:
    k_tbl_trn = "Transit vehicle stops per acre"
    k_trnsvc = 'TrnVehStop_Acre'

    trn_data_prj = transit_svc_measure.transit_svc_density(fc_project, params.trn_svc_fc, project_type)
    trnsvc_project = trn_data_prj[k_trnsvc]

    update_tbl_multiple_geos(loaded_json, trnsvc_project, k_tbl_trn, k_trnsvc, project_commtype)


    # generate map image of bikeway network
    img_obj_bkwy = imgmaker.MakeMapImage(fc_project, "BikeRoutes", project_name)
    bkwy_img_path = img_obj_bkwy.exportMap()
    loaded_json["Bikeway Image Url"] = bkwy_img_path

    # generate heat map image of transit service
    img_obj_trn = imgmaker.MakeMapImage(fc_project, "TransitSvc", project_name)
    trn_img_path = img_obj_trn.exportMap()
    loaded_json["Transit Service Density Image Url"] = trn_img_path


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
    project_fc = arcpy.GetParameterAsText(0)  # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'
    project_name = arcpy.GetParameterAsText(1)  # 'TestTruxelBridge'

    # hard values for testing
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestJefferson'
    # project_name = 'TestJefferson'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_mm_report_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


