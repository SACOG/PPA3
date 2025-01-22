import arcpy

p1 = arcpy.GetParameterAsText(0)

arcpy.AddMessage(f"SUCCESS! Your message is: {p1}")