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
        'lottr_wknd': 'lottr_wknd'
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


def make_congestion_rpt_artsgr(input_dict):

    uis = params.user_inputs
    fc_project = input_dict[uis.geom]
    project_type = input_dict[uis.ptype]
    aadt = input_dict[uis.aadt]
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_SGR}_ReduceCongestion_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get congestion data
    congn_data = npmrds.get_npmrds_data(fc_project, project_type)

    cong_rpt_obj = chart_congestion.CongestionReport(congn_data, loaded_json)
    cong_rpt_obj.update_all_congestion_data()

    # update AADT
    loaded_json["projectAADT"] = aadt

    # log data to run archive table
    output_congn_data = direction_field_translator(in_congdata_dict=congn_data)

    project_uid = utils.get_project_uid(proj_name=input_dict[uis.name], 
                                        proj_type=input_dict[uis.ptype], 
                                        proj_jur=input_dict[uis.jur], 
                                        user_email=input_dict[uis.email])

    data_to_log = {
        'project_uid': project_uid, 'aadt': input_dict[uis.aadt]
        }
        
    data_to_log.update(output_congn_data)

    # NOTE that outputs for arterial sgr congestion report log to same table as those for arterial expansion congestion report.
    utils.log_row_to_table(data_row_dict=data_to_log, dest_table=os.path.join(params.log_fgdb, 'rp_artexp_cong'))

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CongestnRpt{project_name}{output_sufx}.json"

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
    # project_fc = r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestBroadway16th'
    # project_name = 'causeway'
    # jurisdiction = 'Caltrans'
    # project_type = params.ptype_sgr
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
    result_path = make_congestion_rpt_artsgr(input_dict=input_parameter_dict)

    arcpy.SetParameterAsText(9, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


