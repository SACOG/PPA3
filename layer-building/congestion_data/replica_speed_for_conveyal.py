"""
Name: replica_speed_for_conveyal.py
Purpose: Builds speed data SHP for use in Conveyal driving access analysis


Author: Darren Conly
Last Updated: Nov 2024
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path

import pandas as pd
from shapely import wkt
import arcpy
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from scipy.stats.mstats import hmean


def esri_to_df(esri_obj_path, include_geom, field_list=None, index_field=None, 
               crs_val=None, dissolve=False):
    """
    Converts ESRI file (File GDB table, SHP, or feature class) to either pandas dataframe
    or geopandas geodataframe (if it is spatial data)
    esri_obj_path = path to ESRI file
    include_geom = True/False on whether you want resulting table to have spatial data (only possible if
        input file is spatial)
    field_list = list of fields you want to load. No need to specify geometry field name as will be added automatically
        if you select include_geom. Optional. By default all fields load.
    index_field = if you want to choose a pre-existing field for the dataframe index. Optional.
    crs_val = crs, in geopandas CRS string format, that you want to apply to the resulting geodataframe. Optional.
    dissolve = True/False indicating if you want the resulting GDF to be dissolved to single feature.
    """

    fields = field_list # should not be necessary, but was having issues where class properties were getting changed with this formula
    if not field_list:
        fields = [f.name for f in arcpy.ListFields(esri_obj_path)]

    if include_geom:
        import geopandas as gpd
        # by convention, geopandas uses 'geometry' instead of 'SHAPE@' for geom field
        f_esrishp = 'SHAPE@'
        f_gpdshape = 'geometry'
        fields = fields + [f_esrishp]

    data_rows = []
    with arcpy.da.SearchCursor(esri_obj_path, fields) as cur:
        for row in cur:
            rowlist = [i for i in row]
            if include_geom:
                try:
                    geom_wkt = wkt.loads(rowlist[fields.index(f_esrishp)].WKT)
                except:
                    print(f"\tWARNING: not loading link {rowlist} because it has no geometry")
                    continue
                rowlist[fields.index(f_esrishp)] = geom_wkt
            out_row = rowlist
            data_rows.append(out_row)  

    if include_geom:
        fields_gpd = [f for f in fields]
        fields_gpd[fields_gpd.index(f_esrishp)] = f_gpdshape
        
        out_df = gpd.GeoDataFrame(data_rows, columns=fields_gpd, geometry=f_gpdshape)

        # only set if the input file has no CRS--this is not same thing as .to_crs(), which merely projects to a CRS
        if crs_val: out_df.crs = crs_val

        # dissolve to single zone so that, during spatial join, points don't erroneously tag to 2 overlapping zones.
        if dissolve and out_df.shape[0] > 1: 
            out_df = out_df.dissolve() 
    else:
        out_df = pd.DataFrame(data_rows, index=index_field, columns=field_list)

    return out_df

def hmean_nozeroes(row):
    # excludes zero values to compute harmonic mean
    vals = [v for v in row.values if v > 0]

    # if less than 2 available values, return zero as the result--insufficient data
    if len(vals) < 2: result = 0

    # otherwise compute harmonic mean of available values
    result = hmean(vals)

    return result

def load_fc(in_fc, id_field, out_field, desired_pfieldnames, alt_pfieldnames):
    

    use_crs = arcpy.Describe(in_fc).spatialReference.factoryCode

    fc_fields = [f.name for f in arcpy.ListFields(in_fc)]
    v1_check = all([f in fc_fields for f in desired_pfieldnames])
    v2_check = all([f in fc_fields for f in alt_pfieldnames])

    if not v1_check and not v2_check:
        raise Exception(f"none of the candidate fields exist in {in_fc}")
    
    # figure out what correct value field names are
    fields_to_avg = desired_pfieldnames
    if not v1_check: 
        fields_to_avg = alt_pfieldnames
        rename_dict = dict(zip(alt_pfieldnames, desired_pfieldnames))

    # load to dataframe
    print(f"loading {in_fc} using val fields {fields_to_avg}")
    fields = [id_field, *fields_to_avg]
    df = esri_to_df(in_fc, include_geom=True, field_list=fields, crs_val=use_crs)

    # standardize field names
    if not v1_check:
        df = df.rename(columns=rename_dict)
        fields_to_avg = desired_pfieldnames

    # compute harmonic avg of fields_to_avg
    df[out_field] = df[fields_to_avg].apply(lambda row: hmean_nozeroes(row), axis=1)
    df = df[['geometry', id_field, out_field]] # remove unneeded fields

    df = df.loc[(df[out_field] > 0) & (~df[out_field].isnull())] # exclude zero and null values

    return df


if __name__ == '__main__':
    # potential alternative naming schemes for fields
    # arises when different county files use different naming convention for time period fields
    prdfields_v1 = ['wkdy_0700', 'wkdy_0715', 'wkdy_0730', 'wkdy_0745', 'wkdy_0800', 'wkdy_0815', 'wkdy_0830', 'wkdy_0845']
    prdfields_v2 = ['wkdy_28', 'wkdy_29', 'wkdy_30', 'wkdy_31', 'wkdy_32', 'wkdy_33', 'wkdy_34', 'wkdy_35']


    # in_fc = r'I:\Projects\Warren\Replica_Network_update_Sept_2024\Replica_Speed_Data_Darren\Replica_Speed_Data_2\Replica_Speed_Data_2.gdb\Rep_Append'
    fgdb = r'I:\Projects\Warren\Replica_Network_update_Sept_2024\Replica_Speed_Data_Darren\Replica_Speed_Data_2\Replica_Speed_Data_2.gdb'
    fcs = ['qtr_hourly_speeds_2023_el_dorado', 'qtr_hourly_speeds_2023_placer', 'qtr_hourly_speeds_2023_sacramento',
           'qtr_hourly_speeds_2023_yolo', 'qtr_hourly_speeds_2023_yuba', 'qtr_hourly_speeds_2023_sutter']

    out_fgdb = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb'

    out_field = 'spd_7a9a'
    data_year = 2023
    fields_to_avg = ['wkdy_28', 'wkdy_29', 'wkdy_30', 'wkdy_31', 
                     'wkdy_32', 'wkdy_33', 'wkdy_34', 'wkdy_35']
    f_id = 'id'
    # fields_to_load = [f_id, *fields_to_avg]

    #================RUN SCRIPT========================
    # use_crs = arcpy.Describe(in_fc).spatialReference.factoryCode
    # df_in = esri_to_df(in_fc, include_geom=True, field_list=fields_to_load, crs_val=use_crs)
    for i, fc in enumerate(fcs):
        fcp = str(Path(fgdb).joinpath(fc))
        if i == 0:
            df_out = load_fc(fcp, id_field=f_id, out_field=out_field, 
                             desired_pfieldnames=prdfields_v1, alt_pfieldnames=prdfields_v2)
        else:
            df_i = load_fc(fcp, id_field=f_id, out_field=out_field, 
                             desired_pfieldnames=prdfields_v1, alt_pfieldnames=prdfields_v2)
            df_out = pd.concat([df_out, df_i])
        

    # df_in[out_field] = df_in[fields_to_avg].apply(lambda row: hmean_nozeroes(row), axis=1)
    # df_out = df_in[['geometry', f_id, out_field]]
    # df_out = df_out.loc[(df_out[out_field] > 0) & (~df_out[out_field].isnull())] # exclude zero and null values

    # del df_in

    out_name = f'replica_spd_{data_year}_{out_field}'
    out_path = str(Path(out_fgdb).joinpath((out_name)))

    sedf = pd.DataFrame.spatial.from_geodataframe(df_out)
    print(sedf.spatial.to_featureclass(out_path, sanitize_columns=False))

    

