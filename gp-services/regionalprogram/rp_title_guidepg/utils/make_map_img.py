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

    if splitter_element in imgpath_obj.parts:
        stem_start_posn = imgpath_obj.parts.index(splitter_element)
        stempath = Path(*imgpath_obj.parts[stem_start_posn:]).as_posix() 
        output = urljoin(svc_url, stempath)
    else:
        output = "Error when joining root service URL to image URL. Please check root URL and image URL paths."

    return output


class MakeMapImage(object):
    def __init__(self, project_fc, map_name, proj_name='UnnamedProject', imgtyp='PNG'):
        # params from input arguments
        self.proj_name = proj_name
        self.map_name = map_name
        self.project_fc = project_fc #remember, this is a feature set!
        self.project_fc_fnames = [f.name for f in arcpy.ListFields(self.project_fc)]
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

        # FeatureSet input has 'OID' field, while feature class input has 'OBJECTID' field
        oid_options = ['OBJECTID', 'OID']
        f_oid = [f for f in oid_options if f in self.project_fc_fnames][0]
        self.map_sql = f"{f_oid} > 0"

        df = pd.read_csv(self.config_csv)
        row = df.loc[df['MapName'] == self.map_name].reset_index()
        self.map_layout = row['MapLayout'][0]
        self.proj_line_layer = row['ProjLineLayer'][0]
        self.out_map_img = f"{self.map_name}.{self.imgtyp}"


    def expand_ext_2d(self, ext, ratio):
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

            # activate layout and pan to the desired extent and make image of it.
            layouts_aprx = [l.name for l in aprx.listLayouts()] # makes sure there's a corresponding layout in the APRX file to the layout in the CSV
            if self.map_layout in layouts_aprx:
                try:
                    lyt = aprx.listLayouts(self.map_layout)[0]
                    map = aprx.listMaps(self.map_name)[0]
                    
                    if self.proj_line_layer != "":  # ensure there's a feat class for project line
                        
                        try:
                            # Concept: the line template layer in the APRX has its data source updated with the feature class of
                            # the project line, rather than truncating and inserting line feature into same source data set.
                            # Goal is to reduce likelihood of project lines getting mapped to wrong runs.

                            lyr = map.listLayers(self.proj_line_layer)[0] # return layer object--based on layer name, not FC path


                            # This step is twofold: ensures project line project is correct, but
                            # also converts it from feature set to feature class that can be
                            # plugged into APRX
                            sref_lyr = arcpy.Describe(lyr).spatialReference
                            # project_fc_sref = arcpy.Describe(self.project_fc).spatialReference

                            project_fc2 = os.path.join(arcpy.env.scratchGDB, f"pl_prj{int(perf()) + 1}")
                            arcpy.management.Project(self.project_fc, project_fc2, sref_lyr)
                            self.project_fc = project_fc2

                            # get the connection properties of the project line feature class
                            project_fc_info = arcpy.Describe(self.project_fc)
                            project_fc_connprop = {'dataset': project_fc_info.baseName, 
                                                'workspace_factory': 'File Geodatabase', 
                                                'connection_info': {'database': project_fc_info.path}}

                            # update the connection properties of the APRX line layer to connect to the input project line FC
                            # arcpy.AddMessage(f"old connection DB for line layer: {lyr.connectionProperties}")
                            # arcpy.AddMessage(f"should update connection properties to: {project_fc_connprop}")
                            lyr.updateConnectionProperties(lyr.connectionProperties, project_fc_connprop) # https://community.esri.com/t5/python-questions/arcpy-layer-updateconnectionproperties-not-working/td-p/519982
                            
                            # arcpy.AddMessage(f"updated connection DB for line layer: {lyr.connectionProperties}")

                            fl = "fl{}".format(int(perf()))
                            if arcpy.Exists(fl):
                                try:
                                    arcpy.Delete_management(fl)
                                except:
                                    pass 

                            # import pdb; pdb.set_trace()

                            # feature class query based on OBJECTID field, whereas for featureset its OID field.
                            arcpy.MakeFeatureLayer_management(lyr, fl, where_clause=self.map_sql)  # make feature layer of project line
                            
                            ext = ""
                            
                            # method for getting extent for the first element in the project line layer
                            # this method doesn't work if there are multiple features in the line layer
                            # with arcpy.da.SearchCursor(fl, ["Shape@"]) as rows:
                            #     for row in rows:
                            #         geom = row[0]
                            #         ext = geom.extent
                                    
                            #         ext_ratio = 1.33
                            #         ext_zoom = self.expand_ext_2d(ext, ext_ratio)
                            #         break

                            # method for getting extent of the entire line layer, instead of just the first feature in the line layer.
                            mf = lyt.listElements('MAPFRAME_ELEMENT')[0] # get the mapframe from the layout (i.e., the object showing the map)
                            ext = mf.getLayerExtent(lyr) # tight map extent of the project line layer
                            ext_ratio = 1.33
                            ext_zoom = self.expand_ext_2d(ext, ext_ratio) # zooms out from project line a bit to show more context around the project

                            if ext_zoom != "":  # zoom to project line feature
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

                    out_svc_url = set_img_path(params.svc_root_url[0], out_file)
                    

                    return out_svc_url # path to the map image file
                except:
                    arcpy.AddMessage("FAILED AND WENT TO EXCEPTION MODE IN PHASE 2")
                    msg = "{}, {}".format(arcpy.GetMessages(2), trace())
                    arcpy.AddMessage(msg)
                    print(msg)
            else:
                arcpy.AddMessage(f"No map layout found. Map for {self.map_name} will not be created.") # if specified layout isn't in APRX project file, let the user know
        except:
            arcpy.AddMessage("FAILED AND WENT TO EXCEPTION MODE IN PHASE 1. " \
                "ArcPy version may be incompatible with Arc Pro version used to build APRX file. Please check.")
            msg = "{}, {}".format(arcpy.GetMessages(2), trace())
            print(msg)
            arcpy.AddWarning(msg)
            t_returns = (msg,)

if __name__ == '__main__':
    print("Script contains functions only. Do not run this as standalone script.")

    result = set_img_path('https://services.sacog.org/hosting/rest/directories/arcgisjobs', 
                'C:\\arcgisserver\\directories\\arcgisjobs\\rpartexpfreight_gpserver\\jf2567b51a75144c7914b9ac5ddb2dd47\\scratch')

    print(result)





