# https://support.esri.com/en/technical-article/000016853

# List hosted items and the REST endpoint URLs using ArcGIS API for Python

import arcgis
from arcgis.gis import GIS

portal_url = "https://portal.sacog.org/portal"
portal_folder = "PPA_archived_runs"
user = 'DConly@NT-DOMAIN'
gis = GIS(url=portal_url)

items_to_retrieve = ['rp_artexp_vmt', 'rp_artexp_econ', 'rp_artexp_eq', 'rp_artexp_mm', 'rp_artexp_sgr', 
                'rp_fwy_vmt', 'rp_fwy_cong', 'rp_fwy_mm', 'rp_fwy_econ', 'rp_fwy_frgt', 'rp_fwy_saf', 
                'rp_artsgr_sgr', 'cd_compactdev', 'cd_mixeduse', 'cd_houschoice', 'cd_naturpres', 
                'rp_artexp_cong', 'rp_artexp_frgt', 'rp_artexp_saf', 'cd_trnchoice', 'cd_existgasset', 'project_master']

import pdb; pdb.set_trace()

# return URLs for all tables in specified list
# https://support.esri.com/en/technical-article/000024383
resulting_urls = []
for item_name in items_to_retrieve:
    results = gis.content.search(query=f'title:{item_name}, owner:{user}')
    if len(results) > 0:
        item_url = results[0].url
        resulting_urls.append(item_url)
    else:
        print(f'No objects found with name {item_name} and owner {user}')
    

for i in resulting_urls:
    print(i)