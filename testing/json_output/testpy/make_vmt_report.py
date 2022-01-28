"""
Name: make_vmt_report.py
Purpose: creates charts for VMT report for PPA tool
        
          
Author: Darren Conly
Last Updated: Jan 2022
Updated by: <name>
Copyright:   (c) SACOG
Python Version: 3.x
"""

import os
import json

import arcpy

import landuse_buff_calcs as lbuff
import mix_index_for_project as midx
import accessibility_calcs as acc

"""
PSEUDO CODE:
for year 1 and year 2
    get DU and EMP values from landuse_buff_calcs script as dict
for year 1 and year 2
    calc mix index as dict from mix_index_for_project script
calc accessibility as dict from accessibility_calcs scripts
retrieve comm type and region avg values for
    accessibility in year 1 and year 2
    mix index in year 1 and year 2


"""

def get_aggvals(aggvals_csv, metric_name, project_ctype):
    """Gets community type and region values for specified metric_name and
    project community type (project_ctype) by reading from CSV of regional
    and ctype vals (aggvals_csv). Returns dict."""

    col_metricname = 'metric_name'
    df_aggvals = pd.read_csv(aggvals_csv).rename(columns={'Unnamed: 0': col_metricname})
    col_aggvals_year = 'year'
    region_headname = 'REGION'
    cols_ctype_reg = [project_ctype, region_headname, col_aggvals_year]
    aggval_headers = {col: 'CommunityType' for col in df_aggvals.columns if col != region_headname}

    df2 = df_aggvals.loc[df_aggvals[col_metricname] == metric]  # filter to indicated metric
    df2 = df2[cols_ctype_reg]  # only include community types for community types that project is in
    df2 = df2.rename(columns={project_ctype: 'CommunityType'})
    df2 = df2.rename(columns={col:f'{col}' for col in list(df_agg_yr.columns)})

    df2 = df2.set_index(col_aggvals_year)
    dict_out = df2.to_dict(orient='dict')
    # return {metric: dict_out}
    return dict_out




if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

