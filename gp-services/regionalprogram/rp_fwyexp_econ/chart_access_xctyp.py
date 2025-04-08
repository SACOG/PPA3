"""
Name: name_here.py
Purpose: Create JSON config values for making chart of accessibility for one mode by community type


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent)) # enable importing from parent folder

from config_links import params, cfg
import accessibility_calcs as acc_calcs
import get_agg_values as aggvals


def update_json(json_loaded, fc_project, proj_type, project_commtype, weight_pop,
                mode, dest, chart_title, aggval_csv):
    
    k_mode_dest = f"{mode}_{dest}"

    # get list of the geography types in the order they appear in the json file
    geotype_keys = []
    for feature in json_loaded[params.k_charts][chart_title][params.k_features]:
        geotype_keys.append(feature[params.k_attrs][params.k_type])


    # get region and ctype values as dict
    aggval_dict = aggvals.make_aggval_dict(aggval_csv, metric_cols=[k_mode_dest], proj_ctype=project_commtype,
                                    yearkey=params.k_year, geo_regn=params.geo_region)
    output_dict = aggval_dict[k_mode_dest] # remove the top dimension from the dict
    
    # get project-specific values as dict
    acc_cfg = cfg['access_data']
    wgt_tif = Path(acc_cfg['tifdir']).joinpath(acc_cfg['wts'][weight_pop])
    project_dict = acc_calcs.get_acc_data(fc_project, tif_weights=wgt_tif, project_type=proj_type, dest=dest)

    output_dict[params.geo_project] = project_dict[k_mode_dest] # add project-level data to dict with region and ctype vals
    output_dict[params.geo_ctype] = output_dict[project_commtype]

    for i, geo_type in enumerate(geotype_keys):
        json_loaded[params.k_charts][chart_title][params.k_features][i][params.k_attrs][params.k_value] = output_dict[geo_type]

    return project_dict

if __name__ == '__main__':
    pass