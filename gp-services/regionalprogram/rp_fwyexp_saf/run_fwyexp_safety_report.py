"""
Name: run_fwyexp_safety_report.py
Purpose: Safety need subreport for freeway expansion projects


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


import parameters as params
import commtype
import collisions
import get_agg_values as aggvals
import utils.make_map_img as imgmaker

def update_tbl_multiple_geos(json_obj, proj_level_val, k_chartname_metric, metric_outdictkey, proj_commtype):
    """Updates project-level, community-type, and region-level values for simple tables in JSON file."
    """

    ixn_aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[metric_outdictkey], 
                                                proj_ctype=proj_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    val_ctyp = ixn_aggdict[metric_outdictkey][proj_commtype]
    val_regn = ixn_aggdict[metric_outdictkey][params.geo_region]

    json_obj[k_chartname_metric][params.geo_project] = proj_level_val
    json_obj[k_chartname_metric][params.geo_ctype] = val_ctyp
    json_obj[k_chartname_metric][params.geo_region] = val_regn


def make_safety_report_fwyexp(fc_project, project_name, project_type, proj_aadt):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Freeway}_Safety_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)


    # get dict of collision data
    collision_data_project = collisions.get_collision_data(fc_project, project_type, params.collisions_fc, proj_aadt)

    # output example
    #     out_dict = {"TOT_COLLISNS": total_collns, "TOT_COLLISNS_PER_100MVMT": colln_rate_per_vmt,
    #             "FATAL_COLLISNS": fatal_collns, "FATAL_COLLISNS_PER_100MVMT": fatalcolln_per_vmt,
    #             "PCT_FATAL_COLLISNS": pct_fatal_collns, "BIKEPED_COLLISNS": bikeped_collns, 
    #             "BIKEPED_COLLISNS_PER_CLMILE": bikeped_colln_clmile, "PCT_BIKEPED_COLLISNS": pct_bikeped_collns}


    # calculate total collisions
    k_tot_collisions = "TOT_COLLISNS"
    tot_collns = collision_data_project[k_tot_collisions]
    loaded_json["Total collisions"] = tot_collns

    
    # make collision heat map
    img_obj_colln = imgmaker.MakeMapImage(fc_project, "CollisionHeat", project_name)
    colln_img_path = img_obj_colln.exportMap()
    loaded_json["Collision heat map Image Url"] = colln_img_path
    
    # calculate collisions per 100MVMT within all geos
    kv_coll_rate = "TOT_COLLISNS_PER_100MVMT"
    k_tblname_collrate = "Collisions per 100 million VMT"
    colln_rate_proj = collision_data_project[kv_coll_rate]
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=colln_rate_proj,
                            k_chartname_metric=k_tblname_collrate, metric_outdictkey=kv_coll_rate,
                            proj_commtype=project_commtype)


    # chart of fatal collisions within all geos

    k_fatal_collns = "PCT_FATAL_COLLISNS"
    k_chartname_bpfatal = "Share of Collisions that are Fatal"

    val_proj = collision_data_project[k_fatal_collns]
    aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[k_fatal_collns], 
                                                proj_ctype=project_commtype, yearkey=params.k_year, 
                                                geo_regn=params.geo_region, yearval=None)

    val_ctyp = aggdict[k_fatal_collns][project_commtype]
    val_regn = aggdict[k_fatal_collns][params.geo_region]

    vals_dict = {params.geo_project: val_proj, params.geo_ctype: val_ctyp, 
                params.geo_region: val_regn}
        
    features_list = loaded_json[params.k_charts][k_chartname_bpfatal][params.k_features]
    for i, feature in enumerate(features_list):
        f_type = feature[params.k_attrs][params.k_type] # get name of geometry type (project, comm type, region)
        f_val = vals_dict[f_type] # look up the value that corresponds to that geo type
        loaded_json[params.k_charts][k_chartname_bpfatal][params.k_features][i] \
            [params.k_attrs][params.k_value] = f_val # update the JSON file accordingly so each geo type gets correct val



    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"SafetyRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)  
    project_name = arcpy.GetParameterAsText(1)  
    project_aadt = int(arcpy.GetParameterAsText(2))

    # hard values for testing
    # project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\PPAClientRun_SacCity_StocktonBl'
    # project_name = 'TestStockton'
    # project_aadt = 27000

    ptype = params.ptype_fwy
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_safety_report_fwyexp(fc_project=project_fc, project_name=project_name,
                                            project_type=ptype, proj_aadt=project_aadt)

    arcpy.SetParameterAsText(3, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


