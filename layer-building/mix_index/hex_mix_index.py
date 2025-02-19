"""
Name: hex_mix_index.py
Purpose: Compute mix index for each hexagon, based on values inside hexagon (not buffer around hexagon)

    INSTRUCTIONS
    1. Run parcel-to-hex agg script tool (arc toolbox) to compute total jobs and total households in each hex
    2. Run this script on the output feature class to compute new mix index field.


Author: Darren Conly
Last Updated: Feb 2025 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path

import arcpy
import pandas as pd

import parameters as params

# 2/12/2025 IDEA: IMPORT PARCEL2HEX SCRIPT AS A FUNCTION HERE AND YOU CAN MAKE THIS AN "ALL IN ONE" TOOL


def get_wtd_idx(x, facs, params_df):
    output = 0
    
    for fac in facs:
        fac_ratio = '{}_ratio'.format(fac)
        fac_out = x[fac_ratio] * params_df.loc[fac]['weight']
        output += fac_out
    
    return output

def calc_mix_index(in_df, params_df, hh_col, mix_idx_col):
    lu_facs = params_df.index

    # set up for penalty factor for very low density areas.
    area_ac = in_df[params.col_area_ac].values[0]
    dens = (in_df[hh_col].sum() + in_df[params.col_emptot].sum()) / area_ac

    dens_cutoff = 0.5 # if fewer than this many jobs + hh per acre, start penalizing mix score for being in too low-density area
    penaltyfac = min(1, dens / dens_cutoff) # 1 = no penalty
    
    # do mix index calc
    for fac in lu_facs:
        
        # add column for the "ideal", or "balanced" ratio of that land use to HHs
        bal_col = "{}_bal".format(fac) 
        in_df.loc[in_df[hh_col] != 0, bal_col] = in_df[hh_col] * params_df.loc[fac]['bal_ratio_per_hh']
        
        # if no HH, set bal_col = -1
        in_df.fillna(-1)
        
        ratio_col = "{}_ratio".format(fac)
        in_df[ratio_col] = in_df.apply(lambda x: min(x[bal_col], x[fac]) / max(x[bal_col], x[fac]), axis=1)
        
        # if no HH, set ratio col = -1
        in_df.fillna(-1)
        
    in_df[mix_idx_col] = in_df.apply(lambda x: get_wtd_idx(x, lu_facs, params_df), axis=1)
    in_df[mix_idx_col] = in_df[mix_idx_col] * penaltyfac # apply penalty factor for very low density areas (that may have "good" mix)
    
    return in_df

def add_mix_index(hex_fc):
    arcpy.env.overwriteOutput = True
    params_csv = Path(params.config_csvs_dir).joinpath('mix_idx_params.csv')
    mdparams = pd.read_csv(params_csv)

    f_mixidx = 'MIXINDEX'

    # add mix-density field if needed
    fc_names_1 = [f.name for f in arcpy.ListFields(hex_fc)]
    if f_mixidx not in fc_names_1:
        arcpy.management.AddField(hex_fc, f_mixidx, 'SHORT')

    # compute hex size for density calc
    hex_size_ac = get_hex_acres(hex_fc)

    # compute mix density for each hex
    arcpy.AddMessage("computing mix density...")
    curfields = [f_hh, f_emp, f_mixidx]
    with arcpy.da.UpdateCursor(hex_fc, curfields) as ucur:
        for i, row in enumerate(ucur):
            hhcnt = row[curfields.index(f_hh)]
            empcnt = row[curfields.index(f_emp)]
            totnum = hhcnt + empcnt
            totdens = totnum / hex_size_ac
            hhpct = 0
            emppct = 0
            if totnum > 0:
                emppct = empcnt / totnum
                hhpct = hhcnt / totnum

            # mix threshold (not mixed if a "high" percent of either hh or jobs)
            hi_pct = 0.8

            # density threshold (total density per acre)
            low_dens_th = 8
            hi_dens_th = 16

            mixdensity = 0
            try:
                if hhpct >= hi_pct:
                    if totdens <= low_dens_th: mixdensity = 1 # low density residential
                    if totdens > low_dens_th and totdens <= hi_dens_th: mixdensity = 2 # moderate density residential
                    if totdens > hi_dens_th: mixdensity = 3 # high-density residential
                if emppct >= hi_pct:
                    if totdens <= low_dens_th: mixdensity = 4 # low density non-residential
                    if totdens > low_dens_th and totdens <= hi_dens_th: mixdensity = 5 # moderate density non-residential
                    if totdens > hi_dens_th: mixdensity = 6 # high-density non-residential
                if hhpct < hi_pct and emppct < hi_pct:
                    if totdens <= low_dens_th: mixdensity = 7 # low density mixed
                    if totdens > low_dens_th and totdens <= hi_dens_th: mixdensity = 8 # moderate density mixed
                    if totdens > hi_dens_th: mixdensity = 9 # high-density mixed
            except:
                import pdb; pdb.set_trace()

            row[curfields.index(f_mixidx)] = mixdensity
            ucur.updateRow(row)

            if i % 5000 == 0: arcpy.AddMessage(f"{i} hexes processed...")



if __name__ == '__main__':
    hex_fc_in = input('Enter path to hex FC with needed HH and EMP data: ') # r'Q:\SACSIM23\Network\MTPProjectQA_GIS\MTPProjectQA_GIS.gdb\hex_ILUT2050_105_DPS202502130951'
    hhfield = 'HH_TOT_P'
    empfield = 'EMPTOT'

    add_mix_index(hex_fc_in, f_hh=hhfield, f_emp=empfield)
    print("Finished!")