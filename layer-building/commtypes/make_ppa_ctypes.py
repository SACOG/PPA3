"""
Name: make_ppa_ctypes.py
Purpose: Create new ppa-specific community type names to give additional nuance
    (e.g., not treating a small-town downtown like downtown Sacramento)


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path

import pandas as pd
import arcpy


def update_ctypes(input_fc_ctypes, f_ctype_start, f_jur):
    config_csv = Path(__file__).parent.joinpath(r'commtyp_ppa_config.csv')
    f_cfg_jur = 'jur'
    f_cfg_ctyp_plan = 'ctyp_plan'
    f_cfg_ctypfinal = 'ctyp_ppa'

    df_cfg = pd.read_csv(config_csv)

    f_ctyp_final = 'comtyp_ppa_fin'
    fc_fields = [f.name for f in arcpy.ListFields(input_fc_ctypes)]
    if f_ctyp_final not in fc_fields:
        arcpy.management.AddField(input_fc_ctypes, f_ctyp_final, field_type='TEXT')
        
    fields = [f_ctype_start, f_jur, f_ctyp_final]
    with arcpy.da.UpdateCursor(input_fc_ctypes, field_names=fields) as ucur:
        for row in ucur:
            ctplan = row[fields.index(f_ctype_start)]
            jur = row[fields.index(f_jur)]
            
            lkp_results = df_cfg.loc[(df_cfg[f_cfg_ctyp_plan] == ctplan) \
                            & (df_cfg[f_cfg_jur] == jur)][f_cfg_ctypfinal].values
            
            ctppa = ctplan # by default, final ctype is plan ctype
            if len(lkp_results) > 0: # but if specified in config CSV, use that value for final ctype
                ctppa = lkp_results[0]
            row[fields.index(f_ctyp_final)] = ctppa
            ucur.updateRow(row)
    
    print("update completed.")



if __name__ == '__main__':
    fc_ctypes_in = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\Subcommtypes_2025blueprint_final'
    f_ctype_start = 'comtyp_ppa_in'
    f_jur = 'Jurisdiction'

    update_ctypes(fc_ctypes_in, f_ctype_start, f_jur)