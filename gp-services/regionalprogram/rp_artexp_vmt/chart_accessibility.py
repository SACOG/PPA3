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
import pandas as pd

import ppa_input_params as params
from accessibility_calcs import get_acc_data
from get_agg_values import make_aggval_dict



def update_json(json_loaded, fc_project, project_type, project_commtype, aggval_csv, k_chart_title): # "Base Year Service Accessibility" as k_chart_title
    # names in json template --consider migrating to parameters file
    geo_project = "Project"
    geo_ctype = "Community Type"
    geo_region = "Region"

    # re-used json keys, so assign to variable --consider migrating to parameters file
    k_charts = "charts"
    k_features = "features" # remember, this is a list of dicts
    k_attrs = "attributes"
    k_year = "year"
    k_type = "type"

    fc_accessibility_data = params.accdata_fc

    # project level dict of accessibility script outputs
    dict_data = get_acc_data(fc_project, fc_accessibility_data, project_type) 

    # lookup dict between names of data points in raw output and names in JSON file
    dest_type = 'poi2' # destination type as specified in raw data output
    acc_metrics = {f'WALKDESTS{dest_type}':'30 Min Walk', f'BIKEDESTS{dest_type}':'30 Min Biking', 
                    f'AUTODESTS{dest_type}':'15 Min Drive', f'TRANDESTS{dest_type}':'45 Min Transit'}
    accmetrics_keys = list(acc_metrics.keys())

    # trimmed down output, only containing the accessibility metrics needed for this chart 
    # instead of all accessibility metrics
    dict_data2 = {k:dict_data[k] for k in acc_metrics.keys()}

    # make dict of regional and comm type values
    aggval_dict = make_aggval_dict(aggval_csv, metric_cols=accmetrics_keys, proj_ctype=project_commtype, 
                    yearkey=k_year, geo_regn=geo_region)

    for i, k in enumerate(list(acc_metrics.keys())):
        
        # update value for "type" (mode of tranpsortation)
        json_loaded[k_charts][k_chart_title][k_features][i] \
            [k_attrs][k_type] = acc_metrics[k]
        
        # update value for mode's access from project
        json_loaded[k_charts][k_chart_title][k_features][i] \
            [k_attrs][geo_project] = dict_data2[k] 
        
        # update value for mode's access avg for project comm type
        json_loaded[k_charts][k_chart_title][k_features][i] \
            [k_attrs][geo_ctype] = aggval_dict[k][project_commtype] 
        
        # update value for mode's access avg for region
        json_loaded[k_charts][k_chart_title][k_features][i] \
            [k_attrs][geo_region] = aggval_dict[k][geo_region] 

    print("calculated accessibility values sucessfully")


if __name__ == '__main__':
    pass