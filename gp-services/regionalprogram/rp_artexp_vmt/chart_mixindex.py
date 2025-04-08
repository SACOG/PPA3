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
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

from config_links import params
from mix_index_for_project import get_mix_idx
from get_agg_values import make_aggval_dict


def update_json(json_loaded, fc_project, fc_parcel, data_year, proj_type, project_commtype, aggval_csv):

    metname = 'mix_index'
    chart_title = "Land Use Diversity"


    # get list of the geography types in the order they appear in the json file
    geotype_keys = []
    for feature in json_loaded[params.k_charts]["Land Use Diversity"][params.k_features]:
        geotype_keys.append(feature[params.k_attrs][params.k_type])


    # get region and ctype values as dict
    aggval_dict = make_aggval_dict(aggval_csv, metric_cols=[metname], proj_ctype=project_commtype,
                                    yearkey=params.k_year, geo_regn=params.geo_region, yearval=data_year)
    output_dict = aggval_dict[metname] # remove the top dimension from the dict
    
    # get project-specific values as dict
    project_dict = get_mix_idx(fc_parcel, fc_project, proj_type, buffered_pcls=True)
    output_dict[params.geo_project] = project_dict[metname] # add project-level data to dict with region and ctype vals
    output_dict[params.geo_ctype] = output_dict[project_commtype]

    year_label = f"diversity {data_year}"
    for i, geo_type in enumerate(geotype_keys):
        json_loaded[params.k_charts][chart_title][params.k_features][i][params.k_attrs][year_label] = output_dict[geo_type]
            
    print("calculated land use diversity values sucessfully")

    return project_dict


if __name__ == '__main__':
    pass