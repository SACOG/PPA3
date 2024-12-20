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
from zipfile import ZipFile
from pathlib import Path

import pandas as pd
import geopandas as gpd
from arcpy import Describe

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
    f_hwy_ind: str="STATE_HWY_IND"
    f_hwyind_y: str='Y'

    # fields added to resulting data set
    f_fwytag: str="FwyTag"
    f_gcqual: str='gc_qual'

    # CRS values to use
    crs_tims: str='EPSG:4326'
    crs_sacog: str='EPSG:2226'


    def __post_init__(self):
        self.gdf_crashes = self.load_data()



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
        del summary[0]
        
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

        
    def add_fwy_tag(self, road_lines, fwy_query, f_linkid):
        # adds 1/0 tag indicating if crash happend on freeway or non-freeway road.
        # freeway = grade-separated, limited access, high-speed facility
        # or can also be ramp (f_system in (1, 2) OR type = 'P4.0')

        # load road file into gdf with sacog CRS
        crs_roads_native = Describe(road_lines).spatialReference.name
        gdf_roads = esri_to_df(road_lines, include_geom=True, crs_val=crs_roads_native)
        if gdf_roads.geometry[0].geom_type == 'MultiLineString':
            len1 = gdf_roads.shape[0]
            gdf_roads = gdf_roads.to_crs(self.crs_sacog).explode(index_parts=True)
            if gdf_roads.shape[0] != len1:
                print(f"""WARNING: after exploding to get rid of multilinestring objects, 
                      road record count changed from {len1} to {gdf_roads.shape[0]}""")
                
        # filter links to only have links that qualify as freeway links
        gdf_fwys = gdf_roads.query(fwy_query, inplace=False)[['geometry', f_linkid]]

        # add 1/0 indicator flagging all collisions within X ft of a freeway link
        self.gdf_crashes[self.f_fwytag] = 0 # by default, assume not a freeway crash
        cols_to_keep = [c for c in self.gdf_crashes.columns]

        self.gdf_crashes = gpd.sjoin_nearest(self.gdf_crashes, gdf_fwys, how='left', max_distance=100) # spatial join fwy link info to crashes
        self.gdf_crashes.loc[~self.gdf_crashes[f_linkid].isnull(), self.f_fwytag] = 1 # if match found within distance, then update fwytag to say 'yes'

        # if spatially tagged to fwy, but not actually on fwy (e.g. on frontage road next to fwy), then revert fwy tag back to zero ("no")
        self.gdf_crashes.loc[(self.gdf_crashes[self.f_fwytag] == 1) \
                             & (self.gdf_crashes[self.f_hwy_ind] != self.f_hwyind_y), 
                             self.f_fwytag] = 0

        # delete unneeded fields
        for c in self.gdf_crashes.columns:
            if c not in cols_to_keep: del self.gdf_crashes[c]



if __name__ == '__main__':
    collision_data_zip = r"I:\Projects\Darren\PPA3_GIS\CSV\collisions\raw_collisions_region2014_20221128.zip"

    roads_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\NPMRDS_2023ppadata_final'
    road_linkid = 'tmc'
    fwy_qry = f"f_system in (1, 2) or type == 'P4.0'"

    #======================RUN SCRIPT========================

    gdf_out = gpd.GeoDataFrame()
    data_summary = pd.DataFrame()
    with ZipFile(collision_data_zip, 'r') as z:
        for fileobj in z.infolist():
            fname = fileobj.filename
            print(f"Adding collisions from {fname}...")
            if Path(fname).suffix == '.csv':
                with z.open(fname) as f:
                    # import pdb; pdb.set_trace()
                    cobj = CrashDataset(f)
                    cobj.add_fwy_tag(roads_fc, fwy_query=fwy_qry, f_linkid=road_linkid)
                    gdf_out = pd.concat([gdf_out, cobj.gdf_crashes])
                    data_summary = pd.concat([data_summary, cobj.data_summary])

    print("NEXT STEPS: NEED TO EXPORT TO GIS FC AND HAVE USEFUL DATA SUMMARY, EXPORTABLE AS CSV",
          "AND ALSO CONSIDER HAVING EACH CSV APPEND TO  FEATURE CLASS RATHER THAN 1 GIANT DATAFRAME, TO SAVE MEMORY")

    import pdb; pdb.set_trace()