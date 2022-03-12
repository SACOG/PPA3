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


def make_safety_report_artexp(fc_project, project_name, project_type, proj_aadt):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Safety_sample_dataSource.json")

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
    kv_coll_rate = "FATAL_COLLISNS_PER_100MVMT"
    k_tblname_collrate = "Collisions per 100 million VMT"
    colln_rate_proj = collision_data_project[kv_coll_rate]
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=colln_rate_proj,
                            k_chartname_metric=k_tblname_collrate, metric_outdictkey=kv_coll_rate,
                            proj_commtype=project_commtype)


    # Bike ped collision rate per cline mile within all geos
    kv_coll_bkpd = "BIKEPED_COLLISNS_PER_CLMILE"
    k_tblname_collbkpd = "Bike and Ped Collisions per Project Centerline"
    colln_bkpd_proj = collision_data_project[kv_coll_bkpd]
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=colln_bkpd_proj,
                            k_chartname_metric=k_tblname_collbkpd, metric_outdictkey=kv_coll_bkpd,
                            proj_commtype=project_commtype)


    # chart of bike/ped and fatal collisions within all geos
    type_lkp_dict = {"PCT_FATAL_COLLISNS": "Pct of collisions that are fatal",
                    "PCT_BIKEPED_COLLISNS": "Pct of collisions with bike/ped"}

    typekeys = list(type_lkp_dict.keys())

    for i, k in enumerate(typekeys):
        k_chartname_bpfatal = "Fatal and BikePed Collisions"
        typeval = type_lkp_dict[k]
        val_proj = collision_data_project[k]
        aggdict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=[k], 
                                                    proj_ctype=project_commtype, yearkey=params.k_year, 
                                                    geo_regn=params.geo_region, yearval=None)

        val_ctyp = aggdict[k][project_commtype]
        val_regn = aggdict[k][params.geo_region]
        

        loaded_json[params.k_charts][k_chartname_bpfatal][params.k_features][i][params.k_attrs] \
            [params.k_type] = typeval
        loaded_json[params.k_charts][k_chartname_bpfatal][params.k_features][i][params.k_attrs] \
            [params.geo_project] = val_proj
        loaded_json[params.k_charts][k_chartname_bpfatal][params.k_features][i][params.k_attrs] \
            [params.geo_ctype] = val_ctyp
        loaded_json[params.k_charts][k_chartname_bpfatal][params.k_features][i][params.k_attrs] \
            [params.geo_region] = val_regn

        





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
    project_aadt = arcpy.GetParameterAsText(2) 

    # hard values for testing
    # project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\PPAClientRun_SacCity_StocktonBl'
    # project_name = 'TestStockton'
    # project_aadt = 27000

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_safety_report_artexp(fc_project=project_fc, project_name=project_name,
                                            project_type=ptype, proj_aadt=project_aadt)

    arcpy.SetParameterAsText(3, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


