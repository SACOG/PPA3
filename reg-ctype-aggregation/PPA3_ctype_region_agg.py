# --------------------------------
# Name: PPA3_ctype_region_agg.py
# Purpose: testing master script to call can combine all PPA modules
#
#
# Author: Darren Conly
# Last Updated: Sep 2022
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import datetime as dt
from time import perf_counter
from pathlib import Path

import arcpy
import pandas as pd

import parameters as params
import accessibility_calcs as acc
import collisions as coll
import get_buff_netmiles as bufnet
import intersection_density as intsxn
from landuse_buff_calcs import LandUseBuffCalcs
from parcel_data import get_buffer_parcels
import mix_index_for_project as mixidx

import transit_svc_measure as trn_svc

import yaml
yaml_file = Path(__file__).parent.joinpath('config_regavgs.yaml')
with open(yaml_file, 'r') as y:
    pathconfigs = yaml.load(y, Loader=yaml.FullLoader)
    acc_cfg = pathconfigs['access_data']

try:
    arcpy.Delete_management(arcpy.env.scratchGDB) # ensures a new, fresh scratch GDB is created to avoid any weird file-not-found errors
except:
    pass


def get_poly_avg(input_poly_fc, whole_region=False):

    # if scratch GDB weirdly 'becomes' a folder, delete it.
    if arcpy.Describe(arcpy.env.scratchGDB).dataType != 'Workspace': 
        arcpy.Delete_management(arcpy.env.scratchGDB)

    # as of 11/26/2019, each of these outputs are dictionaries
    pcl_pt_data = get_buffer_parcels(params.parcel_pt_fc_yr(), input_poly_fc, buffdist=0, 
                        project_type=params.ptype_area_agg, data_year=params.base_year, 
                        whole_region=whole_region) 

    tifdir = Path(acc_cfg['tifdir'])
    accdata = {}
    acc_combos = {'emp': 'workers', 'nonwork':'pop', 'edu': 'pop'}
    for dest_typ, wtpop in acc_combos.items():
        accdata_i = acc.get_acc_data(fc_project=input_poly_fc, tif_weights=tifdir.joinpath(acc_cfg['wts'][wtpop]),
                                    project_type=params.ptype_area_agg, dest=dest_typ)
        accdata.update(accdata_i)

    collision_data = coll.get_collision_data(input_poly_fc, params.ptype_area_agg, params.collisions_fc, 0)

    mix_data = mixidx.get_mix_idx(pcl_pt_data, input_poly_fc, params.ptype_area_agg, buffered_pcls=True, 
                                  whole_region=True) # always use entirety of pcl_pt_data (whole_region=True) because is always pre-filtered.
    
    intsecn_dens = intsxn.intersection_density(input_poly_fc, params.intersections_base_fc, params.ptype_area_agg)
    bikeway_covg = bufnet.get_bikeway_mileage_share(input_poly_fc, params.ptype_area_agg)
    tran_stop_density = trn_svc.transit_svc_density(input_poly_fc, params.trn_svc_fc, params.ptype_area_agg)

    emp_ind_wtot = LandUseBuffCalcs(pcl_pt_data, input_poly_fc, params.ptype_area_agg,
                                    [params.col_empind, params.col_emptot], buffered_pcls=True).point_sum()
    emp_ind_pct = {'EMPIND_jobshare': emp_ind_wtot[params.col_empind] / emp_ind_wtot[params.col_emptot] \
                   if emp_ind_wtot[params.col_emptot] > 0 else 0}

    pop_x_ej = LandUseBuffCalcs(pcl_pt_data, input_poly_fc, params.ptype_area_agg, [params.col_pop_ilut],
                                buffered_pcls=True, case_field=params.col_ej_ind).point_sum()

    pop_tot = sum(pop_x_ej.values())
    key_yes_ej = max(list(pop_x_ej.keys()))
    pct_pop_ej = {'Pct_PopEJArea': pop_x_ej[key_yes_ej] / pop_tot if pop_tot > 0 else 0}

    job_pop_dens = LandUseBuffCalcs(pcl_pt_data, input_poly_fc, params.ptype_area_agg, \
                                            [params.col_du, params.col_emptot], buffered_pcls=True).point_sum_density()

    out_dict = {}
    for d in [accdata, collision_data, mix_data, intsecn_dens, bikeway_covg, tran_stop_density, pct_pop_ej,\
              emp_ind_pct, job_pop_dens]:
        out_dict.update(d)

    return out_dict

def poly_avg_futyears(input_poly_fc, data_year, whole_region): #IDEALLY could make this part of get_poly_avg as single function with variable number of input args
    pcl_pt_data = get_buffer_parcels(params.parcel_pt_fc_yr(), input_poly_fc, buffdist=0, 
                    project_type=params.ptype_area_agg, data_year=params.future_year, 
                    whole_region=whole_region) 

    mix_data = mixidx.get_mix_idx(pcl_pt_data, input_poly_fc, params.ptype_area_agg, whole_region=whole_region)    
    return mix_data

def get_ppa_agg_data(fc_poly_in, poly_id_field, year_base, year_analysis, whole_region=False, test_run=False):
    """
    Parameters
    ----------
    fc_poly_in : TYPE - polygon feature class
    poly_id_field : TYPE - feature class field
        Feature ID field. Can be name of each feature (e.g. city names, project IDs, etc.), or other unique ID
    test_run : TYPE, optional
        Set to true if you only want to run the first item in the polygon file as a test
    test_val : TYPE, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    df_out : TYPE
        DESCRIPTION.

    """
    
    poly_types_list = []  #based on column values, e.g., distinct community type values.
    
    output_dict = {}

    # create list of ctypes to loop through
    with arcpy.da.SearchCursor(fc_poly_in, [poly_id_field]) as cur:
        for row in cur:
            poly_types_list.append(row[0])
            
    # only do single ctype for test to save time
    if test_run:
        poly_types_list = [poly_types_list[0]]

    # for each ctype, select polygon feature from cytpes fc and export to temporary single feature fc
    for polytype in poly_types_list:
        
        temp_poly_fc = 'TEMP_ctype_fc'
        temp_poly_fc_fp = str(Path(arcpy.env.scratchGDB).joinpath(temp_poly_fc))


        # need to know if search value is a string so that SQL syntax comes out correct
        if type(polytype) == str:
            sql = "{} = '{}'".format(poly_id_field, polytype)
        else:
            sql = "{} = {}".format(poly_id_field, polytype)

        if arcpy.Exists(temp_poly_fc_fp):
            arcpy.Delete_management(temp_poly_fc_fp)
        arcpy.FeatureClassToFeatureClass_conversion(fc_poly_in, arcpy.env.scratchGDB, temp_poly_fc, sql)

        # on that temp fc, run the PPA tools, this will return a dict with all numbers for that ctype
        
        if year_analysis == year_base:
            print(f"\ngetting base year values for {polytype} areas...")
            poly_dict = get_poly_avg(temp_poly_fc_fp, whole_region=whole_region)
        else:
            print("\ngetting {} values for {} areas...".format(year_analysis, polytype))
            poly_dict = poly_avg_futyears(temp_poly_fc_fp, year_analysis, whole_region=whole_region)
        
        output_dict[polytype] = poly_dict
        # for all keys in the output dict, add a tag to the key value to indicate community type
        # append it to a master dict

    
    df_out = pd.DataFrame.from_dict(output_dict, orient='columns')
    return df_out


if __name__ == '__main__':
    time_sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    arcpy.env.workspace = params.fgdb 
    arcpy.OverwriteOutput = True
    base_year = params.base_year
    future_year = params.future_year
    
    # fc of community type polygons
    ctype_fc = params.comm_types_fc
    output_csv = Path(__file__).parent.joinpath(f'Agg_ppa_vals{time_sufx}.csv')
    
    test_run = False
    
    # ------------------RUN SCRIPT-----------------------------------------
    starttm = perf_counter()
    
    # table with fields: poly ID, data values for base year for each ID, but not entire region
    print("getting community type aggregate values")
    df_base_ctypes = get_ppa_agg_data(ctype_fc, params.col_ctype, base_year, base_year, test_run)
    df_future_ctypes = get_ppa_agg_data(ctype_fc, params.col_ctype, base_year, future_year, test_run)

    print("getting regional aggregate values")
    col_region = 'REGION'
    col_year = 'year'
    col_poly_id = 1 # for region feature class, assume only one feature, and this is its OBJECTID column value
    
    df_base_region = get_ppa_agg_data(params.region_fc, "OBJECTID", base_year, base_year, 
                                      whole_region=True, test_run=test_run)
                                      
    df_future_region = get_ppa_agg_data(params.region_fc, "OBJECTID", base_year, future_year,
                                      whole_region=True, test_run=test_run)

    df_base_region = df_base_region.rename(columns={col_poly_id: col_region})
    df_future_region = df_future_region.rename(columns={col_poly_id: col_region})
        
    df_base_all = df_base_ctypes.join(df_base_region)
    df_base_all[col_year] = base_year
    
    df_future_all = df_future_ctypes.join(df_future_region)
    df_future_all[col_year] = future_year

    df_out = pd.concat([df_base_all, df_future_all])                   
    df_out.to_csv(output_csv)
    elapsed = round((perf_counter() - starttm) / 60, 1)
    print(f"summary completed in {elapsed}mins as {output_csv}")
    print("NOTICE: YOU MAY WANT TO HARD-CODE FUTURE-YEAR REGIONAL MIX INDEX = 1.0. ")
    
    # for now, don't do FY mix index for region because base-year region LU mix is the basis for the
    # mix index values. If you want to get regional mix index for FY you'd need
    # to recalculate for the future year.
    # fy_out_dict[region] = poly_avg_futyears(params.region_fc, future_year)
    




