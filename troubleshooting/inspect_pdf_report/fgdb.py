"""
Name: fgdb.py
Purpose: defines elements and parameters relevant to searching
    PPA output file geodatabase for matches in performance outcomes for specified report


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import os
import arcpy
import pandas as pd

# ['rp_artexp_vmt', 'rp_artexp_econ', 'rp_artexp_eq', 'rp_artexp_mm', 'rp_artexp_sgr', 'rp_fwy_vmt', 
# 'rp_fwy_cong', 'rp_fwy_mm', 'rp_fwy_econ', 'rp_fwy_frgt', 'rp_fwy_saf', 'rp_artsgr_sgr', 'cd_compactdev', 'cd_mixeduse', 'cd_houschoice', 
# 'cd_naturpres', 'rp_artexp_cong', 'rp_artexp_frgt', 'rp_artexp_saf', 'cd_trnchoice', 'cd_existgasset', 'TEST_TABLE']

def esri_object_to_df(in_esri_obj, esri_obj_fields, index_field=None):
    '''converts esri gdb table, feature class, feature layer, or SHP to pandas dataframe'''
    data_rows = []
    with arcpy.da.SearchCursor(in_esri_obj, esri_obj_fields) as cur:
        for row in cur:
            out_row = list(row)
            data_rows.append(out_row)

    out_df = pd.DataFrame(data_rows, index=index_field, columns=esri_obj_fields)
    return out_df

class ReportDatabase:
    def __init__(self, fgdb_path):

        self.fgdb_path = fgdb_path
        self.fc_master = 'project_master'

        # fields in project_master table
        self.f_uid = 'project_uid'
        self.f_poutcomes = 'perf_outcomes'

        self.subrpt_dict = {
            "Freeway Expansion": {
                "Reduce VMT": "rp_fwy_vmt",
                "Reduce Congestion": "rp_fwy_cong",
                "Encourage Multimodal Travel": 'rp_fwy_mm',
                "Promote Economic Prosperity": 'rp_fwy_econ',
                "Improve Freight Mobility": 'rp_fwy_frgt',
                "Make a Safer Transportation System": 'rp_fwy_saf'
            },
            "Arterial or Transit Expansion": {
                "Reduce VMT": "rp_artexp_vmt",
                "Reduce Congestion": "rp_artexp_cong",
                "Encourage Multimodal Travel": 'rp_artexp_mm',
                "Promote Economic Prosperity": 'rp_artexp_econ',
                "Improve Freight Mobility": 'rp_artexp_frgt',
                "Make a Safer Transportation System": 'rp_artexp_saf',
                "Promote Complete Streets and State of Good Repair": 'rp_artexp_sgr',
                "Promote Socioeconomic Equity": "rp_artexp_eq"
            },
            "Arterial State of Good Repair": {
                "Reduce VMT": "rp_artexp_vmt",
                "Reduce Congestion": "rp_artexp_cong",
                "Encourage Multimodal Travel": 'rp_artexp_mm',
                "Promote Economic Prosperity": 'rp_artexp_econ',
                "Improve Freight Mobility": 'rp_artexp_frgt',
                "Make a Safer Transportation System": 'rp_artexp_saf',
                "Promote Complete Streets and State of Good Repair": 'rp_artsgr_sgr',
                "Promote Socioeconomic Equity": "rp_artexp_eq"
            }

        }

        fc_pmaster = os.path.join(self.fgdb_path, self.fc_master)
        self.df_pmaster = esri_object_to_df(fc_pmaster, [f.name for f in arcpy.ListFields(fc_pmaster)])

    def check_subrpt_tbl(self, project_uid, project_type, perf_outcome):
        # checks if indicated project uid is in subreport table corresponding
        # to project_Type and project_outcome. 
        try:
            subrpt_tbl = self.subrpt_dict[project_type][perf_outcome]

            sr_tbl_path = os.path.join(self.fgdb_path, subrpt_tbl)
            
            uid_matches = []
            with arcpy.da.SearchCursor(sr_tbl_path, [self.f_uid]) as cur:
                for row in cur:
                    row_uid = row[0]
                    if row_uid == project_uid: uid_matches.append(row_uid)

            # if not matches returned, means that subreport failed to run for the project
            uid_in_subreport = len(uid_matches) > 0
        except:
            uid_in_subreport = f'Warning: keys [{project_type}][{perf_outcome}] do not work. Check reportDatabase.subrpt_dict'

        return uid_in_subreport



if __name__ == '__main__':
    pass