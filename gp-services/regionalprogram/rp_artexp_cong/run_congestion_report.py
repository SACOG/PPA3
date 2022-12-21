"""
Name: run_congestion_report.py
Purpose: calculate numbers for the congestion subreport and produce applicable charts.


Author: Darren Conly
Last Updated: Feb 2022
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
import parcel_data
import chart_job_du_tot
import chart_congestion
import npmrds_data_conflation as npmrds
import utils.utils as utils


def direction_field_translator(in_congdata_dict):

    """Takes in dict with congestion data returned by npmrds_data_conflation module
    and updates its key names so that they match the field names in the gdb table that the run's
    congestion data will be logged to.
    """
    d_dirnames = {
        'NORTHBOUND': 'nb',
        'SOUTHBOUND': 'sb',
        'EASTBOUND': 'eb',
        'WESTBOUND': 'wb'
    }

    d_metrnames = {
        'ff_speed': 'ffspd',
        'havg_spd_worst4hrs': 'congspd',
        'lottr_ampk': 'lottr_am',
        'lottr_midday': 'lottr_md',
        'lottr_pmpk': 'lottr_pm',
        'lottr_wknd': 'lottr_wknd',
        'congrat': 'congrat'
    }
    
    out_dict = {}
    for dname_in, dname_out in d_dirnames.items():
        for mname_in, mname_out in d_metrnames.items():
            congdata_name = f"{dname_in}{mname_in}"
            if congdata_name in in_congdata_dict.keys():
                outval = in_congdata_dict[congdata_name]
            else:
                outval = None

            outdata_name = f"{mname_out}_{dname_out}"

            out_dict[outdata_name] = outval

    return out_dict



def make_congestion_rpt_artexp(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    ptype = input_dict[uis.ptype]
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_ReduceCongestion_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    # for year in data_years:
    #     in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
    #     pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
    #                         buffdist=lu_buffdist_ft, project_type=ptype, data_year=year)
    #     parcel_fc_dict[year] = pcl_buff_fc

    # # calc land use buffer values (job + du totals)

    # d_lubuff = {}
    # for i, year in enumerate(data_years):
    #     in_pcl_pt_fc = parcel_fc_dict[year]
    #     d_jobdu = chart_job_du_tot.update_json(json_loaded=loaded_json, data_year=year, order_val=i, pcl_pt_fc=in_pcl_pt_fc, 
    #                                 project_fc=project_fc, project_type=ptype)

    #     # {f"jobs": jobs, f"dwellingUnits": du}
    #     d_lubuff[year] = d_jobdu

    # job_base = d_lubuff[data_years[0]]["jobs"]
    # job_future = d_lubuff[data_years[1]]["jobs"]
    # du_base = d_lubuff[data_years[0]]["dwellingUnits"]
    # du_future = d_lubuff[data_years[1]]["dwellingUnits"]

    # get congestion data
    congn_data = npmrds.get_npmrds_data(fc_project, project_type)

    cong_rpt_obj = chart_congestion.CongestionReport(congn_data, loaded_json)
    cong_rpt_obj.update_all_congestion_data()

    # get congestion ratio for each direction
    cong_data2 = cong_rpt_obj.parse_congestion()
    import pdb; pdb.set_trace()

    cong_ratios = {f"{k}congrat":v['congestionRatio'] for k, v in cong_data2.items()}
    congn_data.update(cong_ratios)

    # update AADT
    loaded_json["projectAADT"] = aadt

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CongestnRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    # log data to run archive table

    output_congn_data = direction_field_translator(in_congdata_dict=congn_data)
    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    data_to_log = {
        'project_uid': project_uid, 'aadt': input_dict[uis.aadt],
        'jobs_base': job_base, 'jobs_future': job_future, 
        'du_base': du_base, 'du_future': du_future,
        }
    data_to_log.update(output_congn_data)

    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artexp_cong'))

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============

    # inputs from tool interface
    # project_fc = arcpy.GetParameterAsText(0)
    # project_name = arcpy.GetParameterAsText(1)
    # jurisdiction = arcpy.GetParameterAsText(2)
    # project_type = arcpy.GetParameterAsText(3)
    # perf_outcomes = arcpy.GetParameterAsText(4)
    # aadt = arcpy.GetParameterAsText(5)
    # posted_spd = arcpy.GetParameterAsText(6)
    # pci = arcpy.GetParameterAsText(7)
    # email = arcpy.GetParameterAsText(8)

    # hard-coded vals for testing
    project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBroadway16th'
    project_name = 'test'
    jurisdiction = 'test'
    project_type = params.ptype_arterial
    perf_outcomes = 'TEST;Reduce Congestion;Reduce VMT'
    aadt = 30000
    posted_spd = 65   
    pci = 80
    email = 'fake@test.com'

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
    result_path = make_congestion_rpt_artexp(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


