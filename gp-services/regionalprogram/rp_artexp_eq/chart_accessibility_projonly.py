"""
Name: chart_accessibility.py
Purpose: update JSON file for charts that show grouped bar chart of accessibility by
    mode, for project, community type, and region


Author: Darren Conly
Last Updated: Feb 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

import pandas as pd

import parameters as params
import accessibility_calcs as acc_calcs
import get_agg_values as aggvs


def update_json(json_loaded, fc_project, project_type,
                destination_type, k_chart_title, get_ej_only=False):

    fc_accessibility_data = params.accdata_fc

    # project level dict of accessibility script outputs
    dict_data = acc_calcs.get_acc_data(fc_project, fc_accessibility_data, project_type, get_ej=get_ej_only) 

    # lookup dict between names of data points in raw output and names in JSON file
    acc_metrics = {f'WALKDESTS{destination_type}':'30 Min Walk', f'BIKEDESTS{destination_type}':'30 Min Biking', 
                    f'AUTODESTS{destination_type}':'15 Min Drive', f'TRANDESTS{destination_type}':'45 Min Transit'}

    # trimmed down output, only containing the accessibility metrics needed for this chart 
    # instead of all accessibility metrics
    dict_data2 = {k:dict_data[k] for k in acc_metrics.keys()}

    for i, k in enumerate(list(acc_metrics.keys())):
        
        # update value for "type" (mode of tranpsortation)
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.k_type] = acc_metrics[k]
        
        # update value for mode's access from project
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.k_value] = dict_data2[k] 

    print("calculated accessibility values sucessfully")

    return dict_data


if __name__ == '__main__':
    pass