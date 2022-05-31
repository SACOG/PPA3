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


import parameters as params
import commtype
import parcel_data 
import landuse_buff_calcs 
import chart_accessibility_projonly as chart_acc
import get_agg_values as aggvals


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


def make_equity_rpt_artexp(fc_project, project_name, project_type):
    
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

    pop_ej = 0 if len(year_dict) == 1 else year_dict[1]
    pop_non_ej = year_dict[0]

    pop_tot = pop_non_ej + pop_ej

    project_pct_ej = pop_ej / pop_tot if pop_tot > 0 else 0

    k_chartname = "Share of population living in EJ community"
    k_metric = 'Pct_PopEJArea'
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=project_pct_ej, k_chartname_metric=k_chartname,
                            metric_outdictkey=k_metric, proj_commtype=project_commtype)

    # update total EJ population -- NOTE that the JSON tag should be changed from "Population" to "EJ Population"
    loaded_json["Population"] = pop_ej

    # access to jobs chart update
    chart_acc.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type,
                                    k_chart_title="Total Job Accessibility", destination_type='alljob_EJ', 
                                    get_ej_only=True)

    # access to edu facilities chart update
    chart_acc.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type, 
                                    k_chart_title="Education Accessibility", destination_type='edu_EJ', 
                                    get_ej_only=True)

    # access to services chart update
    chart_acc.update_json(json_loaded=loaded_json, fc_project=project_fc, project_type=project_type, 
                                    k_chart_title="Services Accessibility", destination_type='poi2_EJ', 
                                    get_ej_only=True)


    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"EquityRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)  
    project_name = arcpy.GetParameterAsText(1) 

    # test values hard coded
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestLineEastSac'
    # project_name = 'Test'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_equity_rpt_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


