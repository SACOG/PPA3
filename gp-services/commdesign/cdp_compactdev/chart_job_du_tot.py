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

import landuse_buff_calcs as lubuff
import parameters as params

def update_json(json_loaded, data_year, order_val, pcl_pt_fc, project_fc, project_type):
    value_fields = [params.col_emptot, params.col_du]

    out_data = {}
    year_dict = lubuff.LandUseBuffCalcs(pcl_pt_fc, project_fc, project_type, value_fields, 
                                buffered_pcls=True).point_sum()
    out_data[data_year] = year_dict

    # update applicable field values in JSON template
    jobs = out_data[data_year][params.col_emptot]
    du = out_data[data_year][params.col_du]
    k_chart_name = "Jobs and Dwelling"
    json_loaded[params.k_charts][k_chart_name][params.k_features][order_val][params.k_attrs][params.k_year] = str(data_year) # need to convert to string for chart
    json_loaded[params.k_charts][k_chart_name][params.k_features][order_val][params.k_attrs]['jobs'] = jobs
    json_loaded[params.k_charts][k_chart_name][params.k_features][order_val][params.k_attrs]['dwellingUnits'] = du

    print("calculated buffer values sucessfully")


if __name__ == '__main__':
    pass