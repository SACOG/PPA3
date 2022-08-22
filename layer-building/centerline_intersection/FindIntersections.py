# --------------------------------
# Name: Find Intersections
# Purpose: Create intersection feature class from Line feature class.
# Author: Kyle Shipley
# Created: 1/12/18
# Update - 8/22/2022
# Copyright:   (c) SACOG
# Python Version:   3.x
# --------------------------------

import arcpy, os

# Inputs
allstreetlyr = r'I:\Projects\Darren\PPA3_GIS\winuser@GISData.sde\GISData.GISOWNER.RegionalCenterline\GISData.GISOWNER.Regional_Centerline_March_2022'
output = "I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\intersections_2022"
# Enter as True or False
RemoveTwoWayInts = True
KeepCulDeSac = False

#####################################################

arcpy.env.workspace = os.path.dirname(allstreetlyr)
arcpy.env.overwriteOutput = True

print("converting features to intersection points...")
if KeepCulDeSac:
    Int1_lyr = arcpy.FeatureVerticesToPoints_management(allstreetlyr, os.path.join(arcpy.env.scratchGDB, "Int1_lyr"), "BOTH_ENDS")
    arcpy.AddMessage("Keeping Cul De Sacs")
else:
    Int1_lyr = arcpy.Intersect_analysis(allstreetlyr, os.path.join(arcpy.env.scratchGDB, "Int1_lyr"), "ALL", "", "POINT")
arcpy.DeleteIdentical_management(Int1_lyr, "Shape")

print("spatial-joining street network layer onto intersections layer...")
Int2_lyr = arcpy.SpatialJoin_analysis(Int1_lyr, allstreetlyr, os.path.join(arcpy.env.scratchGDB, "Int2_lyr"),"JOIN_ONE_TO_ONE")
whereclause3 = ""
if len(RemoveTwoWayInts) > 0:
    arcpy.AddMessage("Removing Two Way Intersections")
    whereclause3 = '''"Join_Count" <> 2'''
Int3_lyr = arcpy.MakeFeatureLayer_management(Int2_lyr, os.path.join(arcpy.env.scratchGDB, "Int3_lyr"), whereclause3)
arcpy.CopyFeatures_management(Int3_lyr, output)

arcpy.AddMessage("Complete")
