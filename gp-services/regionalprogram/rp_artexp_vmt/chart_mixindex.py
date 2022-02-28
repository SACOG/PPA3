"""
Name: name_here.py
Purpose: Create JSON config values for making the mix index chart, which
    is grouped bar chart showing mix index for base and future year, for project/comm type/region


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
import pandas as pd

import ppa_input_params as params
from mix_index_for_project import get_mix_idx
from get_agg_values import make_aggval_dict


def update_json(json_loaded, fc_project, fc_parcel, data_year, proj_type, project_commtype, aggval_csv):
    # names in json template
    geo_project = "Project"
    geo_ctype = "Community Type"
    geo_region = "Region"

    # re-used json keys, so assign to variable
    k_charts = "charts"
    k_features = "features" # remember, this is a list of dicts
    k_attrs = "attributes"
    k_year = "year"
    k_type = "type"

    metname = 'mix_index'
    chart_title = "Land Use Diversity"


    # get list of the geography types in the order they appear in the json file
    geotype_keys = []
    for feature in json_loaded[k_charts]["Land Use Diversity"][k_features]:
        geotype_keys.append(feature[k_attrs][k_type])


    # get region and ctype values as dict
    aggval_dict = make_aggval_dict(aggval_csv, metric_cols=[metname], proj_ctype=project_commtype,
                                    yearkey=k_year, geo_regn=geo_region)
    output_dict = aggval_dict[metname] # remove the top dimension from the dict
    
    # get project-specific values as dict
    project_dict = get_mix_idx(fc_parcel, fc_project, proj_type, buffered_pcls=True)
    output_dict[geo_project] = project_dict[metname] # add project-level data to dict with region and ctype vals
    output_dict[geo_ctype] = output_dict[project_commtype]

    year_label = f"diversity {data_year}"
    for i, geo_type in enumerate(geotype_keys):
        json_loaded[k_charts][chart_title][k_features][i][k_attrs][year_label] = output_dict[geo_type]
            
    print("calculated land use diversity values sucessfully")



if __name__ == '__main__':
    pass