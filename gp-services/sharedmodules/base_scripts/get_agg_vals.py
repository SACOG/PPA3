
"""
Name: get_agg_vals.py
Purpose: # make dict of region and community type values for specified metric and community type


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
    

def make_aggval_dict(aggval_df, metric_cols, proj_ctype, yearval=None):
    """_summary_

    Args:
        aggval_df (_type_): dataframe of aggregate values, read in from CSV of region and commtype values
        metric_cols (_type_): _description_
        proj_ctype (_type_): _description_
        yearval (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    
    if yearval:
        aggdatadf_proj = aggval_df.loc[(aggval_df[metname_col].isin(metric_cols)) & \
            (aggval_df[k_year] == yearval)] \
            [[metname_col, project_commtype, geo_region, k_year]]
    else:
        aggdatadf_proj = aggval_df.loc[aggval_df[metname_col].isin(metric_cols)] \
            [[metname_col, project_commtype, geo_region, k_year]]

    agg_dict_list = aggdatadf_proj.to_dict(orient='records')

    aggval_dict = {d[metname_col]:{project_commtype:d[proj_ctype], 
                      geo_region:d[geo_region],
                      k_year:d[k_year]} for d in agg_dict_list}

    return aggval_dict


if __name__ == '__main__':
    pass