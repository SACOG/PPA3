"""
Name: run_artexp_safety_report.py
Purpose: Safety need subreport for arterial or transit expansion projects


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
import utils.utils as utils

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


# def make_safety_report_artexp(fc_project, project_name, project_type, proj_aadt):
def make_safety_report_artexp(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype]
    proj_aadt = int(input_dict[uis.aadt])
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Safety_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get project community type
    project_commtype = commtype.get_proj_ctype(project_fc, params.comm_types_fc)

    # project type tag to append to metric field name
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
    img_obj_colln = imgmaker.MakeMapImage(fc_project, "CollisionHeat_NonFwy", project_name)
    colln_img_path = img_obj_colln.exportMap()
    loaded_json["Collision heat map Image Url"] = colln_img_path
    
    # calculate collisions per 100MVMT within all geos
    kv_coll_rate = f"TOT_COLLISNS_PER_100MVMT{project_metric_tag}"
    k_tblname_collrate = "Collisions per 100 million VMT"
    colln_rate_proj = collision_data_project[kv_coll_rate]
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=colln_rate_proj,
                            k_chartname_metric=k_tblname_collrate, metric_outdictkey=kv_coll_rate,
                            proj_commtype=project_commtype)


    # Bike ped collision rate per cline mile within all geos
    kv_coll_bkpd = f"BIKEPED_COLLISNS_PER_CLMILE{project_metric_tag}"
    k_tblname_collbkpd = "Bike and Ped Collisions per Project Centerline"
    colln_bkpd_proj = collision_data_project[kv_coll_bkpd]
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=colln_bkpd_proj,
                            k_chartname_metric=k_tblname_collbkpd, metric_outdictkey=kv_coll_bkpd,
                            proj_commtype=project_commtype)


    # chart of bike/ped and fatal collisions within all geos
    tag_pct_fatal = f"PCT_FATAL_COLLISNS{project_metric_tag}"
    tag_pct_bikeped = f"PCT_BIKEPED_COLLISNS{project_metric_tag}"
    type_lkp_dict = {tag_pct_fatal: "Pct of collisions that are fatal",
                    tag_pct_bikeped: "Pct of collisions with bike/ped"}

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

    # log to data table
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    fatal_crash_pct = collision_data_project[tag_pct_fatal]
    bikeped_crash_pct = collision_data_project[tag_pct_bikeped]

    data_to_log = {
        'project_uid': project_uid, 'crash_cnt': tot_collns, 
        'crash_100mvmt': colln_rate_proj, 'crash_bkpd_clmile': colln_bkpd_proj,
        'crashpct_fatal': fatal_crash_pct, 'crash_bkpd_pct': bikeped_crash_pct
    }


    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artexp_saf'))

    return out_file


if __name__ == '__main__':

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
    result_path = make_safety_report_artexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


