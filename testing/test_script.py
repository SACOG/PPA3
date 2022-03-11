
import arcpy

p_data = ['https://services.sacog.org/hosting/rest/directories/arcgisjobs']
# p_data = 'new_data_source'
arcpy.SetParameterAsText(0, p_data[0])