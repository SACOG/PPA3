"""
Name: job_du_tot.py
Purpose: Make chart of total jobs + total dwelling units


Author: Darren Conly
Last Updated: Feb 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import landuse_buff_calcs
import parameters as params

def update_json(json_loaded, data_year, pcl_pt_fc, project_fc, project_type, value_fields=None):

    tagdict = {params.col_sovtrip_res: "Single-occupant vehicle",
            params.col_hovtrip_res: "Carpool",
            params.col_trntrip_res: "Transit",
            params.col_biketrip_res: "Biking",
            params.col_walktrip_res: "Walking"}

    value_fields = list(tagdict.keys()) + [params.col_persntrip_res]

    year_dict = landuse_buff_calcs.LandUseBuffCalcs(pcl_pt_fc, project_fc, project_type, value_fields, 
                                buffered_pcls=True).point_sum()

    # update applicable field values in JSON template

    total_trips = year_dict[params.col_persntrip_res]

    k_chart_name = "Residential Mode Split"
    k_yeartag = f"{params.k_year} {data_year}"
    for i, mode in enumerate(list(tagdict.keys())):
        mode_label = tagdict[mode]
        mode_share = year_dict[mode] / total_trips
        json_loaded[params.k_charts][k_chart_name][params.k_features][i][params.k_attrs][params.k_type] = mode_label
        json_loaded[params.k_charts][k_chart_name][params.k_features][i][params.k_attrs][k_yeartag] = mode_share

    print("calculated buffer values sucessfully")


if __name__ == '__main__':
    pass