# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_parcel'
g_ESRI_variable_2 = 'fl_project'
# Esri end of added variables

#land use buffer calcs

"""
Get following numbers within 0.5mi of project area:
    sum of jobs
    sum of dwelling units
    sum of trips (for each mode)

"""
import time

import pandas as pd
import geopandas as gpd

import csi_params as params


""" 
# load everything into geodataframes
df_line = gpd.GeoDataFrame.from_file(fgdb, layer=project_line_fc, driver="OpenFileGDB")
df_pcls = gpd.GeoDataFrame.from_file(fgdb, layer=pcl_pts_fc, driver="OpenFileGDB")

# make buffer around line
geom_buffer = df_line.buffer(1320).unary_union
"""

class LandUseBuffCalcs():
    '''
    Class will always automatically calculate the sum totals (e.g. total population) 
    for all parcels within a distance of a project line. Optionally,
    The user can run the point_sum_density() method to get the density (e.g. population density) within the buffer area
    '''
    def __init__(self, gdf_pclpt, gdf_project, project_type, val_fields, buffdist, case_field=None, case_excs_list=[]):
        
        # user inputs
        self.gdf_pclpt = gdf_pclpt
        self.gdf_project = gdf_project
        self.project_type = project_type
        self.val_fields = val_fields
        self.buffdist = buffdist
        self.case_field = case_field
        self.case_excs_list = case_excs_list
        self.selection_buffer = gdf_project.buffer(self.buffdist).unary_union # buffer around project line
        

    def point_sum(self):
        # arcpy.AddMessage("Aggregating land use data...")

        self.selected_pts = self.gdf_pclpt.loc[self.gdf_pclpt.geometry.within(self.selection_buffer) == True]
    
        if self.case_field is not None:
            parcel_df = self.selected_pts.loc[~self.selected_pts[self.case_field].isin(self.case_excs_list)] #exclude specified categories
            out_df = parcel_df.groupby(self.case_field).sum().T # get sum by category (case field)
            # NEXT ISSUE - need to figure out how to show all case types, even if no parcels with that case type within the buffer
        else:
            out_df = pd.DataFrame(self.selected_pts[self.val_fields].sum(axis=0)).T
    
        out_dict = out_df.to_dict('records')[0]
    
        return out_dict
    
    # gets density of whatever you're summing, based on parcel area (i.e., excludes rivers, lakes, road ROW, etc.)
    # considers parcel area for parcels whose centroid is in the buffer. This is because the initial values are based on
    # entire parcels, not parcels that've been chopped by a buffer boundary
    def point_sum_density(self):
    
        # area used in density calculation is land on parcels whose centroid is within the buffer distance. It includes
        # area of entire parcel, both inside and outside the buffer, not "slices" of parcels that are bisected by buffer boundary.
        
        # make sure you calculate the area for normalizing
        if params.col_area_ac not in self.val_fields:
            self.val_fields.append(params.col_area_ac)
    
        #get values (e.g. total pop, total jobs, etc.)
        dict_totals = self.point_sum()
    
        # calculate density per unit of area for each value (e.g. jobs/acre, pop/acre, etc.)
        # This density is based on total parcel area, i.e., even if parts of some of the parcels are outside of the
        # buffer polygon. Since it is density this is a good method (alternative, which would give same answer, is to do
        # the intersect, then divide that area by the area-weighted value (value = pop, emptot, etc.). But this is simpler and
        # gives same density number.
    
        area_unit = "NetPclAcre"
        dict_out = {}
        for valfield, val in dict_totals.items():
            if valfield == params.col_area_ac:
                continue
            else:
                val_density = dict_totals[valfield] / dict_totals[params.col_area_ac]
                dict_out_key = "{}_{}".format(valfield, area_unit)
                dict_out[dict_out_key] = val_density
    
        return dict_out

