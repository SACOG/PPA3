"""
Name: build_config_json.py
Purpose: Facilitate creation of JSON entries for rollup configuration


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import json
import pandas as pd


def strip_decimal(in_val):
    out_val = str(in_val)
    if out_val[-2:] == '.0':
        out_val = out_val[:-2]

    return out_val

if __name__ == '__main__':
    config_csv = r"C:\Users\dconly\GitRepos\PPA3\rollup\chartname_config.csv"
    subreport_name = 'cd_trnchoice'

    #=================RUN SCRIPT=================
    # fields in the config table
    f_makechart = "make_chart"
    f_rptname = 'TableName'
    f_fname = 'FieldName'
    f_dispname = 'DisplayName'
    f_ctemplate = 'chart_template_id'
    f_sort_asc = 'sort_asc_flag'

    template = {
                "targetFieldName": "jobs_added",
                "targetFieldDisplayName": "jobs_added",
                "chartId": "6fdf6349-73f0-4ff6-8f0f-28f6904fed09", # 1/6/2023: chartID value, for now, remains unchanged
                "chartTemplateId": "2",
                "sortAscending": 'true'
                }

    out_list = []

    df = pd.read_csv(config_csv)
    fields_to_use = [f_fname, f_dispname, f_ctemplate, f_sort_asc]
    df = df.loc[(df[f_rptname] == subreport_name) & (df[f_makechart] == 1)][fields_to_use]

    name_dicts = df.to_dict(orient='records') 

    for d in name_dicts:
        t = template
        t["targetFieldName"] = d[f_fname]
        t['targetFieldDisplayName'] = d[f_dispname]
        t["chartTemplateId"] = strip_decimal(d[f_ctemplate]) # remove decimal points and convert to string
        t["sortAscending"] = d[f_sort_asc]
        

        ts = json.dumps(template, indent=4)

        out_list.append(ts)


    for i in out_list:
        print(f"{i},")
