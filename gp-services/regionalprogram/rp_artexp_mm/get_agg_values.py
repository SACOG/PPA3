"""
Name: get_agg_values.py
Purpose: Some PPA charts require getting aggregate values


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import pandas as pd

def make_aggval_dict(aggval_csv, metric_cols, proj_ctype, yearkey, geo_regn,
                    yearval=None):
    """_summary_

    Args:
        aggval_csv (_type_): CSV of all community type and region values for all metrics that need reg/ctype values.
        metric_cols (_type_): The metrics you need ctype and region values for (E.G., walk accessibility avg, industrial jobs share, etc.)
        proj_ctype (_type_): project community type
        yearkey (_type_): year column name in the aggval CSV?
        geo_regn (_type_): What you want the 'REGION' column to be renamed to--CONSIDER REMOVING
        yearval (_type_, optional): year for which you want aggregate data. Defaults to None, which will select all years for the specified metric_cols

    Returns:
        dict: dict of aggregate (region and ctype) values for specified metric_cols for specified yearval (or all available years if yearval not specified)
    """

    df_agg = pd.read_csv(aggval_csv)
    metname_col = "metric_name"
    df_agg = df_agg.rename(columns={'Unnamed: 0':metname_col, 'REGION': geo_regn})
    
    if yearval:
        aggdatadf_proj = df_agg.loc[(df_agg[metname_col].isin(metric_cols)) & \
            (df_agg[yearkey] == yearval)] \
            [[metname_col, proj_ctype, geo_regn, yearkey]]
    else:
        aggdatadf_proj = df_agg.loc[df_agg[metname_col].isin(metric_cols)] \
            [[metname_col, proj_ctype, geo_regn, yearkey]]

    agg_dict_list = aggdatadf_proj.to_dict(orient='records')

    aggval_dict = {d[metname_col]:{proj_ctype:d[proj_ctype], 
                      geo_regn:d[geo_regn],
                      yearkey:d[yearkey]} for d in agg_dict_list}

    return aggval_dict



if __name__ == '__main__':
    pass