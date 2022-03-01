"""
Name: job_du_tot.py
Purpose: Make chart of total jobs + total dwelling units


Author: Darren Conly
Last Updated: Feb 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from landuse_buff_calcs import LandUseBuffCalcs
import parameters as params

def update_json(json_loaded, data_year, order_val, pcl_pt_fc, project_fc, project_type):
    value_fields = ['EMPTOT', 'DU_TOT']

    out_data = {}
    year_dict = LandUseBuffCalcs(pcl_pt_fc, project_fc, project_type, value_fields, 
                                buffered_pcls=True).point_sum()
    out_data[data_year] = year_dict

    # update applicable field values in JSON template
    jobs = out_data[data_year]['EMPTOT']
    du = out_data[data_year]['DU_TOT']
    json_loaded[params.k_charts]["Jobs and Dwelling"][params.k_features][order_val][params.k_attrs]['year'] = data_year
    json_loaded[params.k_charts]["Jobs and Dwelling"][params.k_features][order_val][params.k_attrs]['jobs'] = jobs
    json_loaded[params.k_charts]["Jobs and Dwelling"][params.k_features][order_val][params.k_attrs]['dwellingUnits'] = du

    print("calculated buffer values sucessfully")


if __name__ == '__main__':
    pass