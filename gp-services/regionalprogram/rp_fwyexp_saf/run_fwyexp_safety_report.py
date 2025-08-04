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
arcpy.SetLogHistory(False) # prevents an XML log file from being created every time script is run; long terms saves hard drive space

from config_links import params
import commtype
import collisions
import get_agg_values as aggvals
from utils import make_map_img as imgmaker
from utils import utils as utils

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


def make_safety_report_fwyexp(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype]
    proj_aadt = input_dict[uis.aadt]
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Freeway}_Safety_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)

    # project type tag to append to metric field name
    if project_type not in params.tags_ptypes.keys():
        project_metric_tag = params.tags_ptypes[params.ptypes_fwy[0]]
    else:
        project_metric_tag = params.tags_ptypes[project_type]

    # get dict of collision data
    collision_data_project = collisions.get_collision_data(fc_project, project_type, params.collisions_fc, proj_aadt)

    # update dict keys to reflect project location (freeway or non-freeway)
    collision_data_project = {f"{k}{project_metric_tag}":v for k, v in collision_data_project.items()}

    # output example
    #     out_dict = {"TOT_COLLISNS": total_collns, "TOT_COLLISNS_PER_100MVMT": colln_rate_per_vmt,
    #             "FATAL_COLLISNS": fatal_collns, "FATAL_COLLISNS_PER_100MVMT": fatalcolln_per_vmt,
    #             "PCT_FATAL_COLLISNS": pct_fatal_collns, "BIKEPED_COLLISNS": bikeped_collns, 
    #             "BIKEPED_COLLISNS_PER_CLMILE": bikeped_colln_clmile, "PCT_BIKEPED_COLLISNS": pct_bikeped_collns}


    # calculate total collisions
    k_tot_collisions = f"TOT_COLLISNS{project_metric_tag}"
    tot_collns = collision_data_project[k_tot_collisions]
    loaded_json["Total collisions"] = tot_collns

    
    # make collision heat map
    img_obj_colln = imgmaker.MakeMapImage(fc_project, "CollisionHeat_Fwy", project_name)
    colln_img_path = img_obj_colln.exportMap()
    loaded_json["Collision heat map Image Url"] = colln_img_path
    
    # calculate collisions per 100MVMT within all geos
    kv_coll_rate = f"TOT_COLLISNS_PER_100MVMT{project_metric_tag}"
    k_tblname_collrate = "Collisions per 100 million VMT"
    colln_rate_proj = collision_data_project[kv_coll_rate]
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=colln_rate_proj,
                            k_chartname_metric=k_tblname_collrate, metric_outdictkey=kv_coll_rate,
                            proj_commtype=project_commtype)


    # chart of fatal collisions within all geos

    k_fatal_collns = f"PCT_FATAL_COLLISNS{project_metric_tag}"
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

    # log to data table
    project_uid = utils.get_project_uid(input_dict)


    data_to_log = {
        'project_uid': project_uid, 'crash_cnt': tot_collns,
        'crash_100mvmt': colln_rate_proj, 'crashpct_fatal': val_proj
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_fwy_saf'))

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"SafetyRpt{project_name}{output_sufx}.json"

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
    aadt = int(arcpy.GetParameterAsText(5))
    posted_spd = arcpy.GetParameterAsText(6)
    pci = arcpy.GetParameterAsText(7)
    email = arcpy.GetParameterAsText(8)

    # hard-coded vals for testing
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_I5SMF' # Broadway16th_2226
    # project_name = 'airport'
    # jurisdiction = 'caltrans'
    # project_type = params.ptypes_fwy[0]
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
    result_path = make_safety_report_fwyexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


