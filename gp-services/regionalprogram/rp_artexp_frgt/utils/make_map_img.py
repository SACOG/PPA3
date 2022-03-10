# --------------------------------
# Name: make_map_img.py
# Purpose: Creates a map image as specified by user.
#
# #
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

from pathlib import Path
from urllib.parse import urljoin

import datetime as dt
from time import perf_counter as perf
import pandas as pd

import arcpy

import parameters as params


def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # script name + line number
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe())
    # Get Python syntax error
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

def set_img_path(svc_url, img_path):
    # changes root of img_path to be sacog REST url instead of a file path to local drive.
    # allows the path to be a consumable service
    imgpath_obj = Path(img_path)
    svc_url_obj = Path(svc_url)
    splitter_element = svc_url_obj.parts[-1] # shared element between new root and existing stem
    stem_start_posn = imgpath_obj.parts.index(splitter_element)
    stempath = Path(*imgpath_obj.parts[stem_start_posn:]).as_posix() 
    output = urljoin(svc_url, stempath)

    return output


class MakeMapImage(object):
    def __init__(self, project_fc, map_name, proj_name='UnnamedProject', imgtyp='PNG'):
        # params from input arguments
        self.proj_name = proj_name
        self.map_name = map_name
        self.project_fc = project_fc #remember, this is a feature set!
        self.imgtyp = imgtyp
        
        # params that are derived or imported from ppa_input_params.py
        self.time_sufx = str(dt.datetime.now().strftime('%m%d%Y%H%M'))
        self.config_csv = params.mapimg_configs_csv
        self.img_format = params.map_img_format # jpg, png, etc.
        self.aprx_path = params.aprx_path
        self.proj_line_template_fc = os.path.join(params.fgdb, params.proj_line_template_fc)

        # generate map config attributes
        self.get_map_config_params()

    def get_map_config_params(self):
        df = pd.read_csv(self.config_csv)
        row = df.loc[df['MapName'] == self.map_name].reset_index()
        self.map_layout = row['MapLayout'][0]
        self.map_sql = row['SQL'][0]
        self.proj_line_layer = row['ProjLineLayer'][0]
        self.map_data_layer = row['DataLayer'][0]
        self.out_map_img = f"{self.map_name}.{self.imgtyp}"
     
            
    def expandExtent2D(self, ext, ratio):
        '''Adjust zoom extent for map of project segment
        ext = input extent object
        ratio = how you want to change extent. Ratio > 1 zooms away from project line; <1 zooms in to project line
        '''
        try:
            # spref = ext.spatialReference
            xmin = ext.XMin
            xmax = ext.XMax
            ymin = ext.YMin
            ymax = ext.YMax 
            width = ext.width
            height = ext.height
            dx = (ratio-1.0)*width/2.0 # divided by two so that diff is split evenly between opposite sides, so featur is still center of the extent
            dy = (ratio-1.0)*height/2.0
            xxmin = xmin - dx 
            xxmax = xmax + dx
            yymin = ymin - dy 
            yymax = ymax + dy
            new_ext = arcpy.Extent(xxmin, yymin, xxmax, yymax)
        except:
            new_ext = None 
        return new_ext 
    
    # generates image files from maps
    def exportMap(self):
        arcpy.AddMessage('Generating maps for report...')
        arcpy.env.overwriteOutput = True
        try:
            # create temporary copy of APRX to not have conflicts if 2+ runs done at same time.
            aprx_temp_path = os.path.join(arcpy.env.scratchFolder, "TEMP{}.aprx".format(int(perf()) + 1)) 
            aprx_template_obj = arcpy.mp.ArcGISProject(self.aprx_path)
            aprx_template_obj.saveACopy(aprx_temp_path)
            
            #then manipulate the temporary copy of the APRX
            aprx = arcpy.mp.ArcGISProject(aprx_temp_path)
            

            #insert process to overwrite display layer and append to master. This will update in all layouts using the display layer
            arcpy.DeleteFeatures_management(self.proj_line_template_fc) # delete whatever features were in the display layer
            arcpy.Append_management([self.project_fc], self.proj_line_template_fc, "NO_TEST") # then replace those features with those from user-drawn line

            # activate layout and pan to the desired extent and make image of it.
            layouts_aprx = [l.name for l in aprx.listLayouts()] # makes sure there's a corresponding layout in the APRX file to the layout in the CSV
            if self.map_layout in layouts_aprx:
                try:
                    lyt = aprx.listLayouts(self.map_layout)[0]
                    map = aprx.listMaps(self.map_name)[0]
                    
                    if self.proj_line_layer != "":  # if there's a feat class for project line
                        
                        try:
                            lyr = map.listLayers(self.proj_line_layer)[0] # return layer object--based on layer name, not FC path
                            fl = "fl{}".format(int(perf()))
                            if arcpy.Exists(fl):
                                try:
                                    arcpy.Delete_management(fl)
                                except:
                                    pass 
                            arcpy.MakeFeatureLayer_management(lyr, fl, where_clause=self.map_sql)  # make feature layer of project line
                            ext = ""
                            with arcpy.da.SearchCursor(fl, ["Shape@"]) as rows:
                                for row in rows:
                                    geom = row[0]
                                    ext = geom.extent
                                    
                                    ext_ratio = 1.33
                                    ext_zoom = self.expandExtent2D(ext, ext_ratio)
                                    break
                            if ext_zoom != "":  # zoom to project line feature
                                mf = lyt.listElements('MAPFRAME_ELEMENT')[0]
                                mf.camera.setExtent(ext_zoom)
                                mf.panToExtent(ext_zoom)

                        except:
                            msg = "{}, {}".format(arcpy.GetMessages(2), trace())
                            arcpy.AddMessage(msg)

                    out_file = os.path.join(arcpy.env.scratchFolder, self.out_map_img)

                    if(os.path.exists(out_file)):
                        try:
                            os.remove(out_file)
                        except:
                            pass 
                    if self.img_format.lower() == 'png':
                        lyt.exportToPNG(out_file)
                    elif self.img_format.lower() == 'jpg':
                        lyt.exportToJPEG(out_file) # after zooming in, export the layout to a JPG
                    else:
                        arcpy.AddWarning("Map image {} not created. Must be PNG or JPG.".format(out_file))

                    out_svc_url = set_img_path(params.svc_root_url, out_file)
                    

                    return out_svc_url # path to the map image file
                except:
                    arcpy.AddMessage("FAILED AND WENT TO EXCEPTION MODE IN PHASE 2")
                    msg = "{}, {}".format(arcpy.GetMessages(2), trace())
                    arcpy.AddMessage(msg)
                    print(msg)
            else:
                arcpy.AddMessage(f"No map layout found. Map for {self.map_name} will not be created.") # if specified layout isn't in APRX project file, let the user know
        except:
            arcpy.AddMessage("FAILED AND WENT TO EXCEPTION MODE IN PHASE 1")
            msg = "{}, {}".format(arcpy.GetMessages(2), trace())
            print(msg)
            arcpy.AddWarning(msg)
            t_returns = (msg,)

if __name__ == '__main__':
    print("Script contains functions only. Do not run this as standalone script.")

    result = set_img_path('https://services.sacog.org/hosting/rest/directories/arcgisjobs', 
                'C:\\arcgisserver\\directories\\arcgisjobs\\rpartexpfreight_gpserver\\jf2567b51a75144c7914b9ac5ddb2dd47\\scratch')

    print(result)





