from arcgis.gis import GIS
import arcgis.gis.admin

gis = GIS()
gis_servers = gis.admin.servers.list()
print(dir(gis_servers))
