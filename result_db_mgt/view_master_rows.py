
# script to quickly view if master table updated with new row without locking it
import pandas as pd
# import arcpy
from arcgis.features import GeoAccessor, GeoSeriesAccessor

in_fc = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\PPA3_GIS_SVR\PPA3_run_data.gdb\project_master'

df = pd.DataFrame.spatial.from_featureclass(in_fc)
cols = ['OBJECTID', 'project_uid', 'proj_name', 'time_created',
       'user_email', 'perf_outcomes']

print(df[cols].tail())