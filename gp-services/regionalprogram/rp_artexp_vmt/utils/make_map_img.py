# --------------------------------
# Name: utils.py
# Purpose: Provides general PPA functions that are used throughout various PPA scripts and are not specific to any one PPA script
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


import datetime as dt
import time
import csv

import arcpy

import parameters as params
from utils import trace



class Publish(object):
    def __init__(self, project_fc, ptype, proj_name='UnnamedProject'):
        # params from input arguments
        self.proj_name = proj_name
        self.project_fc = project_fc #remember, this is a feature set!
        
        # params that are derived or imported from ppa_input_params.py
        self.time_sufx = str(dt.datetime.now().strftime('%m%d%Y%H%M'))
        self.out_folder = arcpy.env.scratchFolder
        self.mapimg_configs_csv = params.mapimg_configs_csv
        self.img_format = params.map_img_format # jpg, png, etc.
        self.map_placement_csv = params.map_placement_csv
        self.aprx_path = params.aprx_path
        self.proj_line_template_fc = os.path.join(params.fgdb, params.proj_line_template_fc)

                    
    def build_configs(self):
        in_csv = self.mapimg_configs_csv
        p_map = "MapName" # map that layout and image are derived from
        p_layout = "MapLayout" # layout that will be made into image
        p_where = "SQL" # background data layer (e.g. collision heat layer)
        p_projline = "ProjLineLayer"
        
        out_config_list = []
        
        with open(in_csv, 'r') as f_in:
            reader = csv.DictReader(f_in)
            for row in reader:
                v_map = row[p_map]
                v_layout = row[p_layout]
                v_projline = row[p_projline]
                v_where = row[p_where]
                
                out_config_row = [v_map, v_layout, v_projline, v_where]
                out_config_list.append(out_config_row)
        
        return out_config_list
        

    class PrintConfig(object):
        '''each PrintConfig object has attributes: map frame, layer name, where clause'''
        def __init__(self, l_print_config, imgtyp):
            self.MapFrame = l_print_config[0]   # map/mapframe name
            self.Layout = l_print_config[1]   # layout name
            n_elements = len(l_print_config)
            if(n_elements>1):
                self.Layer = l_print_config[2]    #..layerName used to for zoomto (control ext)
            else:
                self.Layer = ""
            if(n_elements>2):
                self.Where = l_print_config[3]    #..where to get features in the layer.
            else:
                self.Where = ""
    
            self.OutputImageName = "{}.{}".format(self.MapFrame, imgtyp)
            
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
            aprx_temp_path = os.path.join(self.out_folder, "TEMP{}.aprx".format(int(time.clock()) + 1)) 
            aprx_template_obj = arcpy.mp.ArcGISProject(self.aprx_path)
            aprx_template_obj.saveACopy(aprx_temp_path)
            
            #then manipulate the temporary copy of the APRX
            aprx = arcpy.mp.ArcGISProject(aprx_temp_path)
            
            l_print_configs = self.build_configs() # each config list for each image is [map frame name, layout frame name, project line layer name, project feature where clause]
            
            o_print_configs = []
            
            for l_print_config in l_print_configs:
                o_print_config = self.PrintConfig(l_print_config, self.img_format) #converts list vals into attributes of PrintConfig object ('o')
                o_print_configs.append(o_print_config)
            

            #insert process to overwrite display layer and append to master. This will update in all layouts using the display layer
            arcpy.DeleteFeatures_management(self.proj_line_template_fc) # delete whatever features were in the display layer
            arcpy.Append_management([self.project_fc], self.proj_line_template_fc, "NO_TEST") # then replace those features with those from user-drawn line

            for print_config in o_print_configs:
                #only thing needed for this loop is to activate each layout and pan to the desired extent and make image of it.
                layouts_aprx = [l.name for l in aprx.listLayouts()] # makes sure there's a corresponding layout in the APRX file to the layout in the CSV
                if print_config.Layout in layouts_aprx:
                    try:
                        lyt = aprx.listLayouts(print_config.Layout)[0]
                        map = aprx.listMaps(print_config.MapFrame)[0]
                        
                        if print_config.Layer != "":  # if there's a feat class for project line
                            
                            try:
                                lyr = map.listLayers(print_config.Layer)[0] # return layer object--based on layer name, not FC path
                                fl = "fl{}".format(int(time.clock()))
                                if arcpy.Exists(fl):
                                    try:
                                        arcpy.Delete_management(fl)
                                    except:
                                        pass 
                                arcpy.MakeFeatureLayer_management(lyr, fl, where_clause=print_config.Where)  # make feature layer of project line
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
                                
                        out_file = os.path.join(self.out_folder, print_config.OutputImageName)
                        
                        
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
                    except:
                        msg = "{}, {}".format(arcpy.GetMessages(2), trace())
                        arcpy.AddMessage(msg)
                        print(msg)
                else:
                    continue # if specified layout isn't in APRX project file, skip to next map
            t_returns = (params.msg_ok,)
        except:
            msg = "{}, {}".format(arcpy.GetMessages(2), trace())
            print(msg)
            arcpy.AddWarning(msg)
            t_returns = (msg,)

if __name__ == '__main__':
    print("Script contains functions only. Do not run this as standalone script.")





