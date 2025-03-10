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

import arcpy
from arcgis.features import GeoAccessor, GeoSeriesAccessor
if arcpy.Exists(arcpy.env.scratchGDB): arcpy.Delete_management(arcpy.env.scratchGDB)

from esri_file_to_dataframe import esri_to_df

@dataclass
class CrashDataset:
    in_csv: str
    remove_gc_errors: bool=False

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
    f_gcqual: str='gc_issue'

    # fc_regn_boundary: str=r'I:\Projects\Darren\PPA3_GIS\winuser@GISData.sde\GISOWNER.AdministrativeBoundaries\GISOWNER.Counties'

    # CRS values to use
    crs_tims: str='EPSG:4326'
    crs_sacog: str='EPSG:2226'


    def __post_init__(self):
        # unneeded fields to drop:
        self.fields_to_drop = ['OFFICER_ID', 'REPORTING_DISTRICT', 'CHP_SHIFT', 'POPULATION',
                            'CNTY_CITY_LOC', 'SPECIAL_COND', 'BEAT_TYPE', 'CHP_BEAT_TYPE', 'JURIS',
                            'CITY_DIVISION_LAPD', 'CHP_BEAT_CLASS', 'BEAT_NUMBER', 'CALTRANS_COUNTY',
                            'CALTRANS_DISTRICT', 'POSTMILE_PREFIX', 'POSTMILE', 'TOW_AWAY', 
                            'PCF_VIOL_SUBSECTION', 'MVIW', 'MOTORCYCLE_ACCIDENT', 'COUNT_MC_INJURED'
                            'COUNT_MC_KILLED', 'TRUCK_ACCIDENT', 'NOT_PRIVATE_PROPERTY']

        self.gdf_crashes = self.load_data()
        self.minyr = self.gdf_crashes[self.f_colln_year].min()
        self.maxyr = self.gdf_crashes[self.f_colln_year].max()



    def data_quality_summary(self, df): # should this be an "underscore" method?
        """generate data quality report of input data:
            -count with 'good' X/Y values from TIMS
            -count with 'bad' X/Y values from CHP that were truncated
            -count with null/zero X/Y values
            -broken out by county and year

            ***Assumes that TIMS X/Y values are the best***
        """
        

        label_dict = {0: 'Correct lat-long data',
                      1: 'No lat-long data',
                      2: 'Only CHP lat-long data (unreliable)',
                      3: 'Incorrect TIMS lat-long data'}
        
        label_lkp = pd.Series(label_dict).to_frame()

        df = df[[self.f_county, self.f_colln_year, self.f_gcqual]]
        summary = df.value_counts().reset_index()
        summary = summary.merge(label_lkp, left_on=self.f_gcqual, right_index=True, left_index=False)
        summary[self.f_gcqual] = summary[0]
        del summary[0]
        
        return summary

    def tag_wrong_gcs(self, gdf):
        """
        TIMS wrongly geocodes a small percent (~0.1%) of its collisions in significantly wrong location.
        This function flags collisions that are wrong enough that they fall significantly outside of SACOG region.
        NOTE that this flag does not capture collisions whose X/Y values are wrong but still within the SACOG region.
        """
        tolerance_ft = 2500 # count as not in region if more than this many feet outside of the region
        f_dist = 'dist_to_regn'

        fc_regn_boundary: str=r'I:\Projects\Darren\PPA3_GIS\winuser@GISData.sde\GISOWNER.AdministrativeBoundaries\GISOWNER.Counties'
        crs_in = arcpy.Describe(fc_regn_boundary).spatialReference.factoryCode
        gdf_regn = esri_to_df(esri_obj_path=fc_regn_boundary, include_geom=True, 
                              crs_val=crs_in, dissolve=True)
        
        if gdf_regn.crs != gdf.crs: gdf_regn.to_crs(gdf.crs, inplace=True)
        geom_regn = gdf_regn['geometry'].unary_union
        ix = gdf['geometry'].distance(geom_regn)
        ix.name = f_dist
        gdf = gdf.join(ix, how='left')

        # where there is valid TIMS coordinate but point is far outside of region, flag as TIMS GC error
        gdf.loc[(gdf[self.f_x_tims] != 0) & (gdf[f_dist] > tolerance_ft), self.f_gcqual] = 3 

        return gdf



    def load_data(self):
        # loads CSV of collision data to pandas dataframe, removing unused fields
        df_raw = pd.read_csv(self.in_csv)
        rawcols = df_raw.columns
        use_cols = [f for f in rawcols if f not in self.fields_to_drop]
        df_raw = df_raw[use_cols]

        # set null lat-long vals to zero
        df_raw[[self.f_x_tims, self.f_x_chp, self.f_y_tims, self.f_y_chp]] = \
            df_raw[[self.f_x_tims, self.f_x_chp, self.f_y_tims, self.f_y_chp]].fillna(0)

        # load data to geodataframe
        gdf = gpd.GeoDataFrame(df_raw, 
                               geometry=gpd.GeoSeries.from_xy(x=df_raw[self.f_x_tims], 
                                                              y=df_raw[self.f_y_tims], 
                                                              crs=self.crs_tims),
                               ).to_crs(self.crs_sacog)

        # add field for gc quality tag
        gdf[self.f_gcqual] = 0

        # records with no lat-long data from either source
        gdf.loc[(gdf[self.f_x_tims] == 0) & (gdf[self.f_x_chp] == 0), self.f_gcqual] = 1

        # records with no lat-long data from TIMS, but yes from CHP raw (often not reliable)
        gdf.loc[(gdf[self.f_x_tims] == 0) & (gdf[self.f_x_chp] != 0), self.f_gcqual] = 2

        # records with TIMS lat-long data
        gdf.loc[gdf[self.f_x_tims] != 0, self.f_gcqual] = 0

        # records with TIMS lat-long data that fall >2500ft outside of SACOG region (set gcqual = 3)
        gdf = self.tag_wrong_gcs(gdf)

        # get initial data quality summary
        self.data_summary = self.data_quality_summary(gdf)

        # remove records with bad GC data (keep only TIMS gc data for collisions that happened in region)
        if self.remove_gc_errors:
            gdf = gdf.loc[gdf[self.f_gcqual] == 0]

        return gdf

        
    def add_fwy_tag(self, road_lines, fwy_query, f_linkid):
        # adds 1/0 tag indicating if crash happend on freeway or non-freeway road.
        # freeway = grade-separated, limited access, high-speed facility
        # or can also be ramp (f_system in (1, 2) OR type = 'P4.0')

        # load road file into gdf with sacog CRS
        crs_roads_native = arcpy.Describe(road_lines).spatialReference.name
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

        # drop duplicate records
        self.gdf_crashes.drop_duplicates(inplace=True)


if __name__ == '__main__':
    collision_data_zip = r"I:\Projects\Darren\PPA3_GIS\CSV\collisions\raw_collisions2019_2023.zip"
    output_fgdb = r"I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb"

    # seldom-changed variables
    roads_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\NPMRDS_2023ppadata_final'
    road_linkid = 'tmc'
    fwy_qry = f"f_system in (1, 2) or type == 'P4.0'"

    #======================RUN SCRIPT========================
    arcpy.env.overwriteOutput = True

    startyr = 0
    endyr = 0
    partial_files = []
    data_summary = pd.DataFrame()

    with ZipFile(collision_data_zip, 'r') as z:
        for i, fileobj in enumerate(z.infolist()):
            fname = fileobj.filename
            if Path(fname).suffix == '.csv':
                print(f"Adding collisions from {fname}...")
                with z.open(fname) as f:
                    cobj = CrashDataset(f, remove_gc_errors=True)
                    cobj.add_fwy_tag(roads_fc, fwy_query=fwy_qry, f_linkid=road_linkid)
                    if cobj.minyr > 0 & cobj.minyr <= startyr: startyr = cobj.minyr
                    if cobj.maxyr > 0 & cobj.maxyr >= endyr: endyr = cobj.maxyr

                    data_summary = pd.concat([data_summary, cobj.data_summary])

                    sedf = pd.DataFrame.spatial.from_geodataframe(cobj.gdf_crashes)
                    
                    temp_fc = str(Path(arcpy.env.scratchGDB).joinpath(f"TEMP{i}"))
                    sedf.spatial.to_featureclass(temp_fc, sanitize_columns=False)
                    partial_files.append(temp_fc)


    out_fc = str(Path(output_fgdb).joinpath(f"SACOGCollisions{startyr}to{endyr}"))
    arcpy.management.Merge(partial_files, out_fc)

    for tmpfile in partial_files: arcpy.Delete_management(tmpfile)

    # data quality summary
    print("DATA QUALITY SUMMARY:")
    gb = data_summary.groupby('gc_issue')['count'].sum().reset_index()
    nrows = data_summary['count'].sum()
    gcd_rows = gb.loc[gb['gc_issue'] == 'Correct lat-long data']['count'].values[0]
    non_gcd = nrows - gcd_rows
    pct_gcd = f"{gcd_rows / nrows:.2%}"
    print(f"{gcd_rows} out of {nrows} ({pct_gcd}) of collisions have reliable TIMS coordinates. More information:")
    print(gb)
    print(f'\nOutput dataset: {out_fc}')

    # print(data_summary) # KEEP this line in case you want more detailed data quality report

    