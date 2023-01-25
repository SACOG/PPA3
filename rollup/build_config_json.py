"""
Name: build_config_json.py
Purpose: Facilitate creation of JSON entries for rollup configuration
    WHAT THIS SCRIPT DOES:
        For each subreport, specify the correct parameters in the relatedTables:charts list.
        It does NOT update the other key values within each relatedTables item


Author: Darren Conly
Last Updated: Jan 2023
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


def build_subrpt_config(config_csv, subreport_name):
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

    

    df = pd.read_csv(config_csv)
    fields_to_use = [f_fname, f_dispname, f_ctemplate, f_sort_asc]
    df = df.loc[(df[f_rptname] == subreport_name) & (df[f_makechart] == 1)][fields_to_use]

    name_dicts = df.to_dict(orient='records') 

    out_list = []
    for nd in name_dicts:
        t = {} # t = template
        t["targetFieldName"] = nd[f_fname]
        t['targetFieldDisplayName'] = nd[f_dispname]
        t["chartId"] = "6fdf6349-73f0-4ff6-8f0f-28f6904fed09"
        t["chartTemplateId"] = strip_decimal(nd[f_ctemplate]) # remove decimal points and convert to string
        t["sortAscending"] = str(nd[f_sort_asc]).lower()
        
        out_list.append(t)

    return out_list

def build_related_tables(config_csv, tables_objs):
    rt_list = []

    for t in tables_objs:
        tname = t['tableName'].split(' - ')[1]
        chart_list = build_subrpt_config(config_csv, tname)
        t["charts"] = chart_list
        rt_list.append(t)

    return rt_list

if __name__ == '__main__':
    configuration_csv = r"C:\Users\dconly\GitRepos\PPA3\rollup\chartname_config.csv"
    output_json = r"C:\Users\dconly\GitRepos\PPA3\rollup\chartname_config.json"

    json_in = r'C:\Users\dconly\GitRepos\PPA3\rollup\rollup_config_dcedit.json'

    with open(json_in, 'r') as f:
        json_d = json.load(f)

    tables = json_d['relatedTables']
    tablenames = [t['tableName'].split(' - ')[1] for t in tables]

    config_list = build_related_tables(configuration_csv, tables)
    json_out = {"relatedTables": config_list}
    with open(output_json, 'w') as f:
        json.dump(json_out, f, indent=4)
    print(f"Success. Output in {output_json}")

    # for tname in tablenames:
    #     chart_specs = build_subrpt_config(config_csv=configuration_csv, subreport_name=tname)
    #     print(f"{tname}--------------------------------------------------")
    #     for i in chart_specs:
    #         print(f"{i},")

    
