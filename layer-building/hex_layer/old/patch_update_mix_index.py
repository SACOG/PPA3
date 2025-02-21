
"""
Computes updated parcel-level mix index vals per ppa criteria
"""

from pathlib import Path

import arcpy
import pandas as pd

# WARNING - SCRIPT IS MUCH FASTER RUNNING ON FILE GDB THAN VIA SDE
pcl_ilut = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\ilut_combined2020_63_DPS'

mix_idx_config = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\CSV\mix_idx_params.csv"

f_hhcnt = 'HH_TOT_P'
f_mix_idx = 'MIXINDEX'
f_k12 = 'ENR_K12'
f_ret = 'EMPRET'
f_emptot = 'EMPTOT'
f_svc = 'EMPSVC'
f_food = 'EMPFOOD'
f_gisac = 'GISAc'

fields = [f_hhcnt, f_mix_idx, f_k12, f_ret, f_emptot, f_svc, f_food]

non_factors = [f_hhcnt, f_mix_idx]
fac_rows = [f for f in fields if f not in non_factors]

# load config table specifying land use mix factors, ideal ratio, and weights
df_params = pd.read_csv(mix_idx_config)
df_params = df_params.set_index('lu_fac')
ideal_ratios = df_params['bal_ratio_per_hh'].to_dict()
weights = df_params['weight'].to_dict()

def get_row_mixidx(row, fac_fields):
    
    hhcnt = row[f_hhcnt]
    mix_idx = 0

    if hhcnt >= 1: # to make faster, only apply this func to rows where there's at least one hh
        for factor in fac_fields:
            val = row[factor]
            ideal_ratio = ideal_ratios[factor]
            ideal_val = ideal_ratio * row[f_hhcnt]
            
            factor_score = 0
            if max(ideal_val, val) > 0:
                factor_score = min(ideal_val, val) / max(ideal_val, val)
                
            factor_weight = weights[factor]
            mix_idx += factor_score * factor_weight

    return mix_idx


with arcpy.da.UpdateCursor(pcl_ilut, fields) as ucur:
    print("updating mix index values...")
    for i, row in enumerate(ucur):
        rowdict = dict(zip(fields, row))
        mixval = get_row_mixidx(rowdict, fac_rows)
        rowdict[f_mix_idx] = mixval
        newrow = list(rowdict.values())
        ucur.updateRow(newrow)

        if i % 100_000 == 0: print(f"{i} rows processed...")
        
print("""finished. WARNING that these do not consider park acres toward mix value, 
      but they are only weighted 5 percent so should not matter 
      too much for purposes of making screening map""")