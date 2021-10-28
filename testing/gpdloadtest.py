from shapely.geometry.geo import box


""" gpdloadtest.py
Purpose: test to see about selecting parcels within specified distance of a project line,
and comparing speed to arcpy.

RESULT =  slower using geopandas. arcpy can load and select in about 6 seconds. Even with a bounding box
geopandas takes about 18sec """

import geopandas as gpd
import ppa_input_params as params
from time import perf_counter

gdb = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'
fc_project = 'Polylines'
fc_parcels = params.parcel_pt_fc_yr(2016)


st = perf_counter()
gdf_project = gpd.read_file(gdb, driver="FilgeGDB", layer=fc_project)
gdf_projbuff = gdf_project['geometry'][0].buffer(2640)  # geometry of the project line

proj_bbox = gdf_projbuff.bounds

gdf_parcels = gpd.read_file(gdb, driver="FilgeGDB", layer=fc_parcels, bbox=proj_bbox)
gdf_buffpcls = gdf_parcels.loc[gdf_parcels.geometry.within(gdf_projbuff)] # buffer around the project line

elapsed = perf_counter() - st
print(f"loaded and processed in {elapsed} seconds.")
import pdb; pdb.set_trace()