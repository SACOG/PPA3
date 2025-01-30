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
fc_allstreet = r'I:\SDE_Connections\SDE-PPA\owner@PPA.sde\OWNER.RegionalCenterline_2024'
output = "I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\intersections_2024"
# Enter as True or False
RemoveTwoWayInts = True
RemoveRampLinks = True 
KeepCulDeSac = False

#####################################################

arcpy.env.workspace = os.path.dirname(fc_allstreet)
arcpy.env.overwriteOutput = True

print("converting features to intersection points...")
fl_allstreet = 'fl_allstreet'
arcpy.MakeFeatureLayer_management(fc_allstreet, fl_allstreet)

if RemoveRampLinks:
    qry_noramps = "CLASS != 'RAMP'"
    arcpy.SelectLayerByAttribute_management(fl_allstreet, selection_type="NEW_SELECTION", where_clause=qry_noramps)

if KeepCulDeSac:
    Int1_lyr = arcpy.FeatureVerticesToPoints_management(fl_allstreet, os.path.join(arcpy.env.scratchGDB, "Int1_lyr"), "BOTH_ENDS")
    arcpy.AddMessage("Keeping Cul De Sacs")
else:
    Int1_lyr = arcpy.Intersect_analysis(fl_allstreet, os.path.join(arcpy.env.scratchGDB, "Int1_lyr"), "ALL", "", "POINT")
arcpy.DeleteIdentical_management(Int1_lyr, "Shape")

print("spatial-joining street network layer onto intersections layer...")
Int2_lyr = arcpy.SpatialJoin_analysis(Int1_lyr, fl_allstreet, os.path.join(arcpy.env.scratchGDB, "Int2_lyr"),"JOIN_ONE_TO_ONE")
whereclause3 = ""
if RemoveTwoWayInts:
    arcpy.AddMessage("Removing Two Way Intersections")
    whereclause3 = '''"Join_Count" <> 2'''
Int3_lyr = arcpy.MakeFeatureLayer_management(Int2_lyr, os.path.join(arcpy.env.scratchGDB, "Int3_lyr"), whereclause3)
arcpy.CopyFeatures_management(Int3_lyr, output)

arcpy.AddMessage("Complete")
