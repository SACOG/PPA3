"""
Name: name_here.py
Purpose: Create JSON config values for making chart of accessibility for one mode by community type


Author: Darren Conly
Last Updated: 
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
import get_agg_values as aggvals


def update_json(json_loaded, fc_project, fc_accdata, proj_type, project_commtype, 
                k_mode_dest, chart_title, aggval_csv):

    # get list of the geography types in the order they appear in the json file
    geotype_keys = []
    for feature in json_loaded[params.k_charts][chart_title][params.k_features]:
        geotype_keys.append(feature[params.k_attrs][params.k_type])


    # get region and ctype values as dict
    aggval_dict = aggvals.make_aggval_dict(aggval_csv, metric_cols=[k_mode_dest], proj_ctype=project_commtype,
                                    yearkey=params.k_year, geo_regn=params.geo_region)
    output_dict = aggval_dict[k_mode_dest] # remove the top dimension from the dict
    
    # get project-specific values as dict
    project_dict = acc_calcs.get_acc_data(fc_project, fc_accdata, proj_type)
    output_dict[params.geo_project] = project_dict[k_mode_dest] # add project-level data to dict with region and ctype vals
    output_dict[params.geo_ctype] = output_dict[project_commtype]

    for i, geo_type in enumerate(geotype_keys):
        json_loaded[params.k_charts][chart_title][params.k_features][i][params.k_attrs][params.k_value] = output_dict[geo_type]



if __name__ == '__main__':
    pass