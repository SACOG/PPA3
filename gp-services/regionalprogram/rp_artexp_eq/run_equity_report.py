"""
Name: run_equity_report.py
Purpose: Run equity subreport for arterial and transit expansion projects

Author: Darren Conly
Last Updated: Jun 2026
Updated by: Terrell-Tyce
    - Added poverty (<200% FPL) and ethnic breakdown indicators (Darren wishlist items)
    - Fixed project_fc -> fc_project variable name in make_equity_rpt_artexp()
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

from config_links import params
import commtype
import parcel_data
import landuse_buff_calcs
import get_agg_values as aggvals
from utils import utils as utils


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


def update_ethnic_breakdown(json_obj, race_data, pop_tot, proj_commtype):
    """Populates ethnic composition chart with project, community type, and regional shares.

    Regional and community-type values come from Agg_ppa_vals_latest.csv.
    Until that CSV is regenerated (after add_poverty_race_to_parcels.py is run on the
    parcel FC and PPA3_ctype_region_agg.py is re-run), those values will be None.
    """

    ethnic_groups = [
        (params.col_pop_white_nh,   'White non-Hispanic',          'Pct_White_NH'),
        (params.col_pop_afr_am_nh,  'African American non-Hispanic','Pct_AfrAm_NH'),
        (params.col_pop_asian_nh,   'Asian non-Hispanic',           'Pct_Asian_NH'),
        (params.col_pop_other_nh,   'Other non-Hispanic',           'Pct_Other_NH'),
        (params.col_pop_hisp,       'Hispanic/Latino',              'Pct_Hisp'),
    ]

    metric_keys = [mk for _, _, mk in ethnic_groups]
    agg_dict = aggvals.make_aggval_dict(aggval_csv=params.aggval_csv, metric_cols=metric_keys,
                                        proj_ctype=proj_commtype, yearkey=params.k_year,
                                        geo_regn=params.geo_region, yearval=None)

    k_chart = "Ethnic composition of population near project"
    json_obj[k_chart] = {}

    for col, label, metric_key in ethnic_groups:
        pct_proj = race_data.get(col, 0) / pop_tot if pop_tot > 0 else 0
        val_ctyp = agg_dict[metric_key][proj_commtype]
        val_regn = agg_dict[metric_key][params.geo_region]

        json_obj[k_chart][label] = {
            "Within project location": pct_proj,
            "Within community type": val_ctyp,
            "Within region": val_regn,
        }


def make_equity_rpt_artexp(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_name = input_dict[uis.name]
    project_type = input_dict[uis.ptype]

    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_Equity_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [params.base_year]

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


    # ===== POPULATION IN EJ AREAS =====
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


    # ===== POVERTY: % OF POPULATION IN HH EARNING < 200% FEDERAL POVERTY LEVEL =====
    # Requires pop_pov200 field on parcel FC (see layer-building/parcel_census_combine/add_poverty_race_to_parcels.py)
    pov_fields = [params.col_pop_ilut, params.col_pop_pov200]
    pov_data = landuse_buff_calcs.LandUseBuffCalcs(base_buff_pcl_fc, fc_project, project_commtype,
                pov_fields, buffered_pcls=True).point_sum()

    pop_pov200 = pov_data.get(params.col_pop_pov200, 0)
    pct_pov200 = pop_pov200 / pop_tot if pop_tot > 0 else 0

    k_chartname_pov = "Share of population in households below 200% federal poverty level"
    k_metric_pov = 'Pct_Pov200'
    update_tbl_multiple_geos(json_obj=loaded_json, proj_level_val=pct_pov200, k_chartname_metric=k_chartname_pov,
                            metric_outdictkey=k_metric_pov, proj_commtype=project_commtype)


    # ===== ETHNIC BREAKDOWN =====
    # Requires pop_white_nh, pop_afr_am_nh, pop_asian_nh, pop_other_nh, pop_hisp fields on parcel FC
    # (see layer-building/parcel_census_combine/add_poverty_race_to_parcels.py)
    race_cols = [params.col_pop_ilut, params.col_pop_white_nh, params.col_pop_afr_am_nh,
                 params.col_pop_asian_nh, params.col_pop_other_nh, params.col_pop_hisp]
    race_data = landuse_buff_calcs.LandUseBuffCalcs(base_buff_pcl_fc, fc_project, project_commtype,
                race_cols, buffered_pcls=True).point_sum()

    update_ethnic_breakdown(loaded_json, race_data, pop_tot, project_commtype)


    # ===== LOG TO DATA TABLE =====
    project_uid = utils.get_project_uid(input_dict)

    data_to_log = {
        'project_uid': project_uid,
        'pop_tot': pop_tot, 'pop_ej_area': pop_ej,
        'pctpot_ej_area': project_pct_ej,
        'pop_pov200': pop_pov200, 'pct_pov200': pct_pov200,
        'p_white_nh': race_data.get(params.col_pop_white_nh, 0),
        'p_afr_am_nh': race_data.get(params.col_pop_afr_am_nh, 0),
        'p_asian_nh': race_data.get(params.col_pop_asian_nh, 0),
        'p_other_nh': race_data.get(params.col_pop_other_nh, 0),
        'p_hisp': race_data.get(params.col_pop_hisp, 0),
    }

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artexp_eq'))


    # ===== WRITE OUTPUT JSON =====
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
