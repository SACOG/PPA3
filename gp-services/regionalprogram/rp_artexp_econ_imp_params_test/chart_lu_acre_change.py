"""
Name: job_du_tot.py
Purpose: Make chart comparing base vs. future year quantity of specified land use type


Author: Darren Conly
Last Updated: Feb 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import get_lutype_acres as get_acres
import parameters as params

def update_json(json_loaded, data_year, order_val, fc_poly_parcels, project_fc, project_type,
                in_lu_type, k_chart_title):
    
    lu_rpt_obj = get_acres.GetLandUseArea(project_fc, project_type, fc_poly_parcels)
    lu_rpt_dict_year = lu_rpt_obj.get_lu_acres(in_lu_type)

    # update applicable field values in JSON template
    data_key = f'net_{in_lu_type}_acres'
    lutype_acres = lu_rpt_dict_year[data_key]
    json_loaded[params.k_charts][k_chart_title][params.k_features][order_val][params.k_attrs][params.k_year] = str(data_year) # JSON chart requires year label to be string
    json_loaded[params.k_charts][k_chart_title][params.k_features][order_val][params.k_attrs][params.k_value] = lutype_acres

    output_dict = {data_key: lutype_acres}

    return output_dict

if __name__ == '__main__':
    pass