"""
Name: line_based_isochrone.py
Purpose: Generates isochrones for user-specified line using OpenRouteService API.
    References:
        -https://openrouteservice.org/
        -https://openrouteservice.org/dev/#/api-docs/v2/isochrones/{profile}/post
        
          
Author: Darren Conly
Last Updated: Nov 2021
Updated by: <name>
Copyright:   (c) SACOG
Python Version: 3.x
"""

import os
import requests
import geopandas as gpd
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import arcpy
arcpy.env.overwriteOutput = True

class ORSPointIsochrone:
    def __init__(self, api_file, start_pts_arr, isoc_type, range_mins_or_mi, trav_mode, output_type):
        """Generates an isochrone (time- or distance-based buffer polygon) around

        Args:
            api_file ([type]): one-line text file containing the ORS API key
            start_pts_arr(2d list array): list of starting points. Has format [[x1, y1], [x2, y2], etc.]
            isoc_type (string): whether the iso is time- or distance-based
            range_mins_or_mi (int): max time or distance from origin point
            trav_mode (string): travel mode used
        """

        self.trav_modes = ["driving-car", "foot-walking", "cycling-regular"]
        self.isoc_types = ["time", "distance"] # whether you want isochrone based on time or distance

        self.api_key = self.get_api_key(api_file)
        self.isoc_type = isoc_type
        self.trav_mode = trav_mode
        self.start_pts = start_pts_arr
        self.range = self.get_range(range_mins_or_mi)
        self.output_type = output_type

    def get_api_key(self, api_txtfile):
        """Takes in api_textfile and returns string containing ORS API key"""
        with open(api_txtfile, 'r') as f:
            api_key = f.readline()
        return api_key

    def get_range(self, in_range_val):
        """Takes the user's in_range_val (minutes for time-based isochrone 
        or miles for distance) and converts them to ORS's range units
        (seconds for time; meters for distance)"""
        if self.isoc_type == "time":
            out_val = self.isoc_size * 60 # convert minutes to seconds, which ORS uses
        elif self.isoc_type == "distance":
            out_val = self.isoc_size * 1609.34 # convert miles to meters
        else:
            raise Exception(f"""Isochrone type must be either 'distance' or 'time'. 
            '{self.isoc_type}'' is not an acceptable value.""")

    def make_isochrone(self):
        """Make call to the ORS API for specified parameters, and return polygon as a geod"""
        body = {"locations":self.start_pts, "range":[self.range], "range_type":self.isoc_type}

        headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': self.api_key,
        'Content-Type': 'application/json; charset=utf-8'
        }

        call = requests.post(f'https://api.openrouteservice.org/v2/isochrones/{self.trav_mode}', 
            json=body, headers=headers)

        if self.output_type = 'geodataframe':
            out_iso = gpd.GeoDataFrame.from_features(call.json()['features'])
        elif self.output_type = 'json_txt':
            out_iso = call.text
        
        return out_iso




        





