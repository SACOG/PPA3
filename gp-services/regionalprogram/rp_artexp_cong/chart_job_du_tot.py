"""
Name: job_du_tot.py
Purpose: Make chart of jobs + dwelling unit density (per net parcel acre)


Author: Darren Conly
Last Updated: Feb 2022
Updated by:
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

from landuse_buff_calcs import LandUseBuffCalcs
from config_links import params
from get_agg_values import make_aggval_dict


def update_json(json_loaded, data_year, order_val, pcl_pt_fc, project_fc, project_type,
                project_commtype, aggval_csv):
    value_fields = [params.col_emptot, params.col_du]
    k_jobs_dens = f"{params.col_emptot}_NetPclAcre"
    k_du_dens   = f"{params.col_du}_NetPclAcre"

    year_dict = LandUseBuffCalcs(pcl_pt_fc, project_fc, project_type, value_fields,
                                 buffered_pcls=True).point_sum_density()

    jobs_dens = year_dict[k_jobs_dens]
    du_dens   = year_dict[k_du_dens]

    # look up community-type and region density benchmarks
    aggval_dict = make_aggval_dict(aggval_csv, metric_cols=[k_jobs_dens, k_du_dens],
                                   proj_ctype=project_commtype, yearkey=params.k_year,
                                   geo_regn=params.geo_region, yearval=data_year)

    commtype_jobs = aggval_dict.get(k_jobs_dens, {}).get(project_commtype, 0)
    region_jobs   = aggval_dict.get(k_jobs_dens, {}).get(params.geo_region, 0)
    commtype_du   = aggval_dict.get(k_du_dens, {}).get(project_commtype, 0)
    region_du     = aggval_dict.get(k_du_dens, {}).get(params.geo_region, 0)

    k_chart_name = "Jobs and Dwelling"
    attrs = json_loaded[params.k_charts][k_chart_name][params.k_features][order_val][params.k_attrs]
    attrs[params.k_year]   = str(data_year)
    attrs['jobs']          = jobs_dens
    attrs['dwellingUnits'] = du_dens
    attrs['commtype_jobs'] = commtype_jobs
    attrs['region_jobs']   = region_jobs
    attrs['commtype_du']   = commtype_du
    attrs['region_du']     = region_du

    return {'jobs': jobs_dens, 'dwellingUnits': du_dens}


if __name__ == '__main__':
    pass