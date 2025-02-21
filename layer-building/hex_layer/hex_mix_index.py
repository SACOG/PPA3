
"""
Computes updated hex-level mix index vals per ppa criteria
"""

from pathlib import Path

import arcpy
import pandas as pd

def get_hex_acres(in_fc):
    # compute, just once, the area of a hex. Since all hexes are same size,
    # no need to recompute area for every mix index row calc.
    with arcpy.da.SearchCursor(in_fc, 'SHAPE@AREA') as scur:
        for row in scur:
            area = row[0]
            break

    srcode = arcpy.Describe(in_fc).spatialReference.factoryCode
    if srcode != 2226:
        arcpy.AddWarning("WARNING: spatial ref is not 2226. Conversion to acres will not be correct.")

    return area / 43_560 # convert sq feet to acres

def compute_hex_mixdix(in_hex_fc):
    # load config table specifying land use mix factors, ideal ratio, and weights
    mix_idx_config = r"\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\CSV\mix_idx_params.csv"
    df_params = pd.read_csv(mix_idx_config)
    df_params = df_params.set_index('lu_fac')
    ideal_ratios = df_params['bal_ratio_per_hh'].to_dict()
    weights = df_params['weight'].to_dict()
    facfields = list(df_params.index)

    f_mix_idx = 'MIXINDEX'
    f_hhcnt = 'HH_TOT_P'
    f_emp = 'EMPTOT'

    hex_ac = get_hex_acres(in_hex_fc)

    hexfields1 = [f.name for f in arcpy.ListFields(in_hex_fc)]
    if f_mix_idx not in hexfields1:
        arcpy.management.AddField(in_hex_fc, f_mix_idx, 'FLOAT')

    missingfields = [f for f in facfields if f not in hexfields1]
    if len(missingfields) > 0:
       arcpy.AddWarning(f"ERROR: these needed input fields are missing from hex feature class: {missingfields}")
       import pdb;pdb.set_trace()

    def get_row_mixidx(row, f_hh, facfields, dens_cutoff=0.5):
        # dens_cutoff: if hex contains fewer than this many jobs + hh per acre, then
        # penalize the mix index to avoid high score for areas with good mix but very little (e.g. 1 house + 0.5 retail jobs)
        hhcnt = row[f_hh]
        mix_idx = 0

        if hhcnt >= 1: # to make faster, only apply this func to rows where there's at least one hh
            
            # penalize mix-index score if density is too low (i.e., "good" mix of nearly nothing)
            emp = row[f_emp]
            dens = (hhcnt + emp) / hex_ac
            penaltyfac = min(1, dens / dens_cutoff) # 1 = no penalty

            for factor in facfields:
                val = row[factor]
                ideal_ratio = ideal_ratios[factor]
                ideal_val = ideal_ratio * row[f_hh]
                
                factor_score = 0
                if max(ideal_val, val) > 0:
                    factor_score = min(ideal_val, val) / max(ideal_val, val)
                    
                factor_weight = weights[factor]
                mix_idx += factor_score * factor_weight

            mix_idx *= penaltyfac # apply penalty factor

        return mix_idx

    ucur_fields = [*facfields, f_hhcnt, f_mix_idx]
    with arcpy.da.UpdateCursor(in_hex_fc, ucur_fields) as ucur:
        print("updating mix index values...")
        for i, row in enumerate(ucur):
            rowdict = dict(zip(ucur_fields, row))
            mixval = get_row_mixidx(rowdict, f_hhcnt, facfields)
            rowdict[f_mix_idx] = mixval
            newrow = list(rowdict.values())
            ucur.updateRow(newrow)

            if i % 5000 == 0: print(f"{i} rows processed...")
            
    print("""finished.""")

if __name__ == '__main__':
    input_hexes = input("Enter path to hex layer with needed fields for mix index computation: ")

    compute_hex_mixdix(input_hexes)