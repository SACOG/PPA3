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

config_csv = r"C:\Users\dconly\GitRepos\PPA3\rollup\chartname_config.csv"
subreport_name = 'rp_artexp_frgt'

update_template_id = True
chart_template_id = "2" # must be string--consider whether you want this template ID to apply to ALL charts in this report!

#=================RUN SCRIPT=================
f_rptname = 'rptname'
f_fname = 'fname'
f_dispname = 'dispname'
f_ctemplate = 'chart_template'

template = {
            "targetFieldName": "jobs_added",
            "targetFieldDisplayName": "jobs_added",
            "chartId": "6fdf6349-73f0-4ff6-8f0f-28f6904fed09",
            "chartTemplateId": "2",
            "sortAscending": 'true'
			}

out_list = []

df = pd.read_csv(config_csv)
df = df.loc[df['rptname'] == subreport_name][[f_fname, f_dispname, f_ctemplate]]

name_dict = df.to_dict(orient='records') 

for d in name_dict:
    t = template
    t["targetFieldName"] = d[f_fname]
    t['targetFieldDisplayName'] = d[f_dispname]

    if update_template_id:
        t["chartTemplateId"] = d[f_ctemplate]

    ts = json.dumps(template, indent=4)

    out_list.append(ts)


for i in out_list:
    print(f"{i},")
