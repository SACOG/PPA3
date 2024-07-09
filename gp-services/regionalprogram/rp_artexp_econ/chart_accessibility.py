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

def update_json(json_loaded, fc_project, project_type, project_commtype, aggval_csv, k_chart_title): # "Base Year Service Accessibility" as k_chart_title

    # project level dict of accessibility script outputs
    # dict_data = get_acc_data(fc_project, fc_accessibility_data, project_type) 
    
    accdir = acc_cfg['acc_dir']
    popdata = Path(accdir).joinpath(acc_cfg['wts']['pop'])
    dict_data = get_acc_data(fc_project, popdata, project_type)
    import pdb; pdb.set_trace()

    # lookup dict between names of data points in raw output and names in JSON file
    # 7/8/2024 - MUST change these to adapt to new dict_data keys! Pending whether we want to still use cutoffs, decay curves, etc.
    # acc_metrics = {f'WALKDESTS{destination_type}':'30 Min Walk', f'BIKEDESTS{destination_type}':'30 Min Biking', 
    #                 f'AUTODESTS{destination_type}':'15 Min Drive', f'TRANDESTS{destination_type}':'45 Min Transit'}
    keydict = {} # format correctly for chart tick mark names
    for k in dict_data.keys():
        modename = k.split('_')[0]
        keydict[modename] = modename.title()

    # accmetrics_keys = list(acc_metrics.keys())

    # trimmed down output, only containing the accessibility metrics needed for this chart 
    # instead of all accessibility metrics
    # dict_data2 = {k:dict_data[k] for k in acc_metrics.keys()}

    # make dict of regional and comm type values
    aggval_dict = make_aggval_dict(aggval_csv, metric_cols=dict_data.keys(), proj_ctype=project_commtype, 
                    yearkey=params.k_year, geo_regn=params.geo_region)

    # for i, k in enumerate(list(acc_metrics.keys())):
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
            [params.k_attrs][params.geo_ctype] = aggval_dict[k][project_commtype] 
        
        # update value for mode's access avg for region
        json_loaded[params.k_charts][k_chart_title][params.k_features][i] \
            [params.k_attrs][params.geo_region] = aggval_dict[k][params.geo_region] 

    print("calculated accessibility values sucessfully")

    return dict_data2


if __name__ == '__main__':
    pass