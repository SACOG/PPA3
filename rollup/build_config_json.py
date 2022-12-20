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
from csv import DictReader
from shlex import join


template = {
            "targetFieldName": "jobs_added",
            "targetFieldDisplayName": "jobs_added",
            "chartId": "6fdf6349-73f0-4ff6-8f0f-28f6904fed09",
            "chartTemplateId": "2",
            "sortAscending": 'true'
			}

out_list = []

with open(r"C:\Users\dconly\GitRepos\PPA3\rollup\chartname_config.csv", 'r') as f:
    reader = DictReader(f)
    for row in reader:
        t = template
        t["targetFieldName"] = row['fname']
        t['targetFieldDisplayName'] = row['dispname']

        ts = json.dumps(template, indent=4)

        out_list.append(ts)


for i in out_list:
    print(f"{i},")
