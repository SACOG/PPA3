import sys

import arcpy

sys.path.append(r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\gpconfig')
import parameters as params

# testv = arcpy.GetParameterAsText(0)
arcpy.AddMessage(f"success - test value = {params.region_fc}")