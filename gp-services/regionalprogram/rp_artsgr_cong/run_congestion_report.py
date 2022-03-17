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


def make_congestion_rpt_artexp(fc_project, project_name, project_type, aadt):
    
    in_json = os.path.join(params.json_templates_dir, "SACOG_{Regional Program}_{Arterial_SGR}_ReduceCongestion_sample_dataSource.json")

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)

    # get congestion data
    congn_data = npmrds.get_npmrds_data(fc_project, project_type)

    cong_rpt_obj = chart_congestion.CongestionReport(congn_data, loaded_json)
    cong_rpt_obj.update_all_congestion_data()

    # update AADT
    loaded_json["projectAADT"] = aadt

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CongestnRpt{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0) # r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge'  # 
    project_name = arcpy.GetParameterAsText(1) # 'TestTruxelBridge' #  
    proj_aadt = int(arcpy.GetParameterAsText(2)) # 32000 # 

    # test values
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestJefferson'  # 
    # project_name = 'Jefferson' #  
    # proj_aadt = 32000 # 

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = make_congestion_rpt_artexp(fc_project=project_fc, project_name=project_name, project_type=ptype, aadt=proj_aadt)

    arcpy.SetParameterAsText(3, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


