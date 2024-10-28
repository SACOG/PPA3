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

from pathlib import Path

import parameters as params
from accessibility_calcs import get_acc_data
from get_agg_values import make_aggval_dict

import yaml
yaml_file = os.path.join(os.path.dirname(__file__), 'data_paths.yaml')
with open(yaml_file, 'r') as y:
    pathconfigs = yaml.load(y, Loader=yaml.FullLoader)
    acc_cfg = pathconfigs['access_data']

def update_json(json_loaded, fc_project, project_type, project_commtype, destination_type, weight_pop, aggval_csv, k_chart_title):

    # project level dict of accessibility script outputs
    # dict_data = get_acc_data(fc_project, fc_accessibility_data, project_type) 
    
    accdir = acc_cfg['tifdir']
    weights = Path(accdir).joinpath(acc_cfg['wts'][weight_pop]) # population with which to weight avg accessibility (e.g. total pop, workers, etc.)
    dict_data = get_acc_data(fc_project, weights, project_type, destination_type)

    # 7/8/2024 - MUST change these to adapt to new dict_data keys! Pending whether we want to still use cutoffs, decay curves, etc.
    # make dict of regional and comm type values
    aggval_dict = make_aggval_dict(aggval_csv, metric_cols=dict_data.keys(), proj_ctype=project_commtype, 
                    yearkey=params.k_year, geo_regn=params.geo_region)

    for i, modename in enumerate(list(dict_data.keys())):
        
        # update value for "type" (mode of tranpsortation)
        chart_tickname = modename.split('_')[0].title()
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.k_type] = chart_tickname # acc_metrics[k]
        
        # update value for mode's access from project
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.geo_project] = dict_data[modename]
        
        # update value for mode's access avg for project comm type
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.geo_ctype] = aggval_dict[modename][project_commtype] 
        
        # update value for mode's access avg for region
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.geo_region] = aggval_dict[modename][params.geo_region] 

    print("calculated accessibility values sucessfully")

    return dict_data


if __name__ == '__main__':
    pass