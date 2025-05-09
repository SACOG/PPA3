#land use buffer calcs

"""
Get following numbers within buffer distance of project line:
    sum of jobs
    sum of dwelling units
    sum of trips (for each mode)

"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__))) # enable importing from parent folder

from time import perf_counter as perf

import arcpy
arcpy.env.overwriteOutput = True

import pandas as pd

import parameters as params

class LandUseBuffCalcs():
    '''
    Class will always automatically calculate the sum totals (e.g. total population) 
    for all parcels within a distance of a project line. Optionally,
    The user can run the point_sum_density() method to get the density (e.g. population density) within the buffer area
    '''
    def __init__(self,fc_pclpt, fc_project, project_type, val_fields, buffered_pcls=False, 
                buffdist=0, case_field=None, case_excs_list=[]):
        
        # user inputs
        self.fc_pclpt = fc_pclpt
        self.fc_project = fc_project
        self.project_type = project_type
        self.val_fields = val_fields
        self.buffdist = buffdist
        self.case_field = case_field
        self.case_excs_list = case_excs_list
        self.buffered_pcls = buffered_pcls
        

    def point_sum(self):
        arcpy.AddMessage("Aggregating land use data...")
        
        sufx = int(perf()) + 1
        fl_parcel = os.path.join('memory','fl_parcel{}'.format(sufx))

        if arcpy.Exists(fl_parcel): arcpy.Delete_management(fl_parcel)
        arcpy.MakeFeatureLayer_management(self.fc_pclpt, fl_parcel)
        
        if not self.buffered_pcls:
            # if a pre-made set of parcels within a buffer was not specified, then
            # do the parcel selection process here--makes it much slower!
            fl_project = 'fl_project'
            if arcpy.Exists(fl_project): arcpy.Delete_management(fl_project)
            arcpy.MakeFeatureLayer_management(self.fc_project, fl_project)    

            buff_dist = 0 if self.project_type == params.ptype_area_agg else self.buffdist
            arcpy.SelectLayerByLocation_management(fl_parcel, "WITHIN_A_DISTANCE", fl_project, buff_dist)
    
        # If there are no points in the buffer (e.g., no collisions on segment, no parcels, etc.),
        # still add those columns, but make them = 0
        file_len = arcpy.GetCount_management(fl_parcel)
        file_len = int(file_len.getOutput(0))
    
        if self.case_field is not None:
            self.val_fields.append(self.case_field)
    
        # load parcel data into dataframe
        rows_pcldata = []
        with arcpy.da.SearchCursor(fl_parcel, self.val_fields) as cur:
            for row in cur:
                df_row = list(row)
                rows_pcldata.append(df_row)
    
        parcel_df = pd.DataFrame(rows_pcldata, columns = self.val_fields)
    
        if self.case_field is not None:
            parcel_df = parcel_df.loc[~parcel_df[self.case_field].isin(self.case_excs_list)] #exclude specified categories
            out_df = parcel_df.groupby(self.case_field).sum().T # get sum by category (case field)
            # NEXT ISSUE - need to figure out how to show all case types, even if no parcels with that case type within the buffer
        else:
            out_df = pd.DataFrame(parcel_df[self.val_fields].sum(axis=0)).T
    
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


if __name__ == '__main__':
    arcpy.env.workspace = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb'

    # input fc of parcel data--must be points!
    # input line project for basing spatial selection
    project_fc = r'I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\Polylines'
    ptype = params.ptype_arterial
    data_years = [params.base_year, params.future_year]
    buffdist_ft = 2640
    value_fields = ['POP_TOT', 'EMPTOT', 'EMPIND', 'PT_TOT_RES', 'SOV_TOT_RES', 'HOV_TOT_RES', 'TRN_TOT_RES',
                    'BIK_TOT_RES', 'WLK_TOT_RES']
    # value_fields = ['EMPIND']

    out_data = {}
    for data_year in data_years:
        in_pcl_pt_fc = params.parcel_pt_fc_yr(data_year)
        year_dict = LandUseBuffCalcs(in_pcl_pt_fc, project_fc, ptype, value_fields, buffdist_ft).point_sum()
        out_data[data_year] = year_dict

    print(out_data)
    

