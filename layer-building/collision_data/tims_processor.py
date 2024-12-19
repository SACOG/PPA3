"""
Name: tims_processor.py
Purpose: Takes in TIMS from UC Berkeley Transportation Injury Mapping System (TIMS)
    and creates single regional GIS layer of collision locations along with a summary of
    data completeness.

    TIMS REFERENCE - https://tims.berkeley.edu/help/SWITRS.php


Author: Darren Conly
Last Updated: Jan 2025
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from dataclasses import dataclass

import pandas as pd
import geopandas as gpd

from esri_file_to_dataframe import esri_to_df

@dataclass
class CrashDataset:
    in_csv: str

    # fields from TIMS data. May need periodic updating as field names can change.
    f_case_id: str='CASE_ID'
    f_colln_year: str='ACCIDENT_YEAR'
    f_x_tims: str='POINT_X'
    f_y_tims: str='POINT_Y'
    f_x_chp: str='LONGITUDE'
    f_y_chp: str='LATITUDE'
    f_county: str='COUNTY'

    # fields added to resulting data set
    f_fwytag: str="FwyTag"
    f_gcqual: str='gc_qual'

    # CRS values to use
    crs_tims: str='EPSG:4326'
    crs_sacog: str='EPSG:2226'


    def __post_init__(self):
        self.gdf_crashes = self.load_data(self.in_csv)



    def data_quality_summary(self, df): # should this be an "underscore" method?
        """generate data quality report of input data:
            -count with 'good' X/Y values from TIMS
            -count with 'bad' X/Y values from CHP that were truncated
            -count with null/zero X/Y values
            -broken out by county and year

            ***Assumes that TIMS X/Y values are the best***
        """
        

        label_dict = {0: 'No lat-long data',
                      1: 'Only CHP lat-long data (unreliable)',
                      2: 'Complete lat-long data'}
        
        label_lkp = pd.Series(label_dict).to_frame()

        df = df[[self.f_county, self.f_colln_year, self.f_gcqual]]
        summary = df.value_counts().reset_index()
        summary = summary.merge(label_lkp, left_on=self.f_gcqual, right_index=True, left_index=False)
        summary[self.f_gcqual] = summary[0]
        
        return summary



    def load_data(self):
        # loads CSV of collision data to geopandas geodataframe
        df_raw = pd.read_csv(self.in_csv)

        # set null lat-long vals to zero
        df_raw[[self.f_x_tims, self.f_x_chp]] = df_raw[[self.f_x_tims, self.f_x_chp]].fillna(0)

        # add field for gc quality tag
        df_raw[self.f_gcqual] = 0

        # records with no lat-long data from either source
        df_raw.loc[(df_raw[self.f_x_tims] == 0) & (df_raw[self.f_x_chp] == 0), self.f_gcqual] = 0

        # records with no lat-long data from TIMS, but yes from CHP raw (often not reliable)
        df_raw.loc[(df_raw[self.f_x_tims] == 0) & (df_raw[self.f_x_chp] != 0), self.f_gcqual] = 1

        # records with TIMS lat-long data
        df_raw.loc[df_raw[self.f_x_tims] != 0, self.f_gcqual] = 2

        # get data quality summary
        self.data_summary = self.data_quality_summary(df_raw)

        # remove records with bad GC data (keep only TIMS gc data)
        df_raw = df_raw.loc[df_raw[self.f_gcqual] == 2]


        # load data to geodataframe
        gdf = gpd.GeoDataFrame(df_raw, 
                               geometry=gpd.GeoSeries.from_xy(x=df_raw[self.f_x_tims], 
                                                              y=df_raw[self.f_y_tims], 
                                                              crs=self.crs_tims),
                               ).to_crs(self.crs_sacog)

        return gdf

        
    def add_fwy_tag(self, road_lines, road_type_field, road_fwy_types):
        # adds 1/0 tag indicating if crash happend on freeway or non-freeway road.
        # freeway = grade-separated, limited access, high-speed facility
        # or can also be ramp (f_system in (1, 2) OR type = 'P4.0')
        gdf_roads = esri_to_df(road_lines, include_geom=True, crs_val=self.crs_sacog)

        import pdb; pdb.set_trace()





if __name__ == '__main__':
    collision_csv = r"I:\Projects\Darren\PPA3_GIS\CSV\collisions\raw_collisions_region2014_20221128\collisions_ELD_2014.csv"

    cobj = Dataset(collision_csv)
    cobj.load_data()
