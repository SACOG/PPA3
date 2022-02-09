"""
Name: get_aggdata.py
Purpose: calculates aggregate data for community type and region avgs for PPA numbers
        
          
Author: Darren Conly
Last Updated: Jan 2022
Updated by: <name>
Copyright:   (c) SACOG
Python Version: 3.x
"""

import pandas as pd


def get_aggvals(aggvals_csv, metric_name, project_ctype):
    col_metricname = 'metric_name'
    df_aggvals = pd.read_csv(aggvals_csv).rename(columns={'Unnamed: 0': col_metricname})
    col_aggvals_year = 'year'
    region_headname = 'REGION'
    cols_ctype_reg = [project_ctype, region_headname, col_aggvals_year]
    aggval_headers = {col: 'CommunityType' for col in df_aggvals.columns if col != region_headname}
    

    df2 = df_aggvals.loc[df_aggvals[col_metricname] == metric_name]  # filter to indicated metric
    df2 = df2[cols_ctype_reg]  # only include community types for community types that project is in
    df2 = df2.rename(columns={project_ctype: 'CommunityType'})
    df2 = df2.rename(columns={col:f'{col}' for col in list(df2.columns)})

    df2 = df2.set_index(col_aggvals_year)
    dict_out = df2.to_dict(orient='index')
    return {metric_name: dict_out}

if __name__ == '__main__':
    aggvals_csv = r"C:\Users\dconly\GitRepos\PPA2\ppa\Input_Template\CSV\Agg_ppa_vals04222020_1017.csv"

    metric = 'mix_index'  # 'WALKDESTSalljob' # 'mix_index'
    project_commtype = "Arterials & Suburban Corridors"

    output = get_aggvals(aggvals_csv, metric, project_commtype)
    print(output)
