"""
Name: run_cd_housingchoice_rpt..py
Purpose: Housing choice subreport for community design projects


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

import landuse_buff_calcs as lubuff
import parameters as params
import parcel_data 


def cd_housingchoice_rpt(fc_project, project_name, project_type):
    # sometimes the scratch gdb folder becomes just a folder, so need to re-create to ensure no errors
    if arcpy.Exists(arcpy.env.scratchGDB): arcpy.Delete_management(arcpy.env.scratchGDB)

    in_json = os.path.join(params.json_templates_dir, "SACOG_{Community Design Program}_{CommDesign}_HousingChoice_sample_dataSource.json")
    lu_buffdist_ft = params.ilut_sum_buffdist # land use buffer distance
    data_years = [2016, 2040]

    with open(in_json, "r") as j_in: # load applicable json template
        loaded_json = json.load(j_in)


    # get parcels within buffer of project, make FC of them
    parcel_fc_dict = {}
    for year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(year)
        pcl_buff_fc = parcel_data.get_buffer_parcels(fc_pclpt=in_pcl_pt_fc, fc_project=fc_project,
                            buffdist=lu_buffdist_ft, project_type=project_type, data_year=year)
        parcel_fc_dict[year] = pcl_buff_fc

    # calc housing types split
    for i, year in enumerate(data_years):
        pcl_fc = parcel_fc_dict[year]

        housing_mix_data = lubuff.LandUseBuffCalcs(pcl_fc, project_fc, project_type, [params.col_du], params.du_mix_buffdist,
                                            case_field=params.col_housing_type, case_excs_list=['Other']).point_sum()

        types = ["Very Low or Rural Res Density", "Low Density", "Medium Density",
                "Med-High Density", "High Density", "Mixed Use"]

        k_chartname = "Housing Types"
        loaded_json[params.k_charts][k_chartname][params.k_features][i] \
            [params.k_attrs][params.k_year] = str(year)

        for htyp in types:
            if htyp in housing_mix_data.keys():
                val = housing_mix_data[htyp]
            else:
                val = 0
            
            loaded_json[params.k_charts][k_chartname][params.k_features][i] \
                [params.k_attrs][htyp] = val
                                      

    # write out to new JSON file
    output_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    out_file_name = f"CDHousingChoice{project_name}{output_sufx}.json"

    out_file = os.path.join(output_dir, out_file_name)
    
    with open(out_file, 'w') as f_out:
        json.dump(loaded_json, f_out, indent=4)

    return out_file


if __name__ == '__main__':

    # ===========USER INPUTS THAT CHANGE WITH EACH PROJECT RUN============


    # specify project line feature class and attributes
    project_fc = arcpy.GetParameterAsText(0)
    project_name = arcpy.GetParameterAsText(1)

    # hard values for testing
    # project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\TestJefferson'
    # project_name = 'TestJefferson'

    ptype = params.ptype_arterial
    

    #=================BEGIN SCRIPT===========================
    arcpy.env.workspace = params.fgdb
    output_dir = arcpy.env.scratchFolder
    result_path = cd_housingchoice_rpt(fc_project=project_fc, project_name=project_name, project_type=ptype)

    arcpy.SetParameterAsText(2, result_path) # clickable link to download file
        
    arcpy.AddMessage(f"wrote JSON output to {result_path}")


