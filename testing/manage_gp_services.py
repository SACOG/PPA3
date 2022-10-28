
# https://gis.miamigov.com/portal/portalhelp/en/server/latest/develop/windows/example-edit-service-properties.htm
import requests
import json

from arcgis.gis import GIS


portal_url = "https://portal.sacog.org/portal" # "https://services.sacog.org/hosting"# "https://portal.sacog.org/portal"
username = "NT-DOMAIN\dconly" # input('Enter your Portal Username: ')  # "NT-DOMAIN\dconly"
gis = GIS(portal_url, username)

rptg = gis.content.search('RPTitleAndGuide')[0]
url_json = f"{rptg.url}?f=pjson"

json_start = requests.get(url_json).json()

json_start["maxInstancesPerNode"] = 5
json_updated = json.dumps(json_start)

import pdb; pdb.set_trace()