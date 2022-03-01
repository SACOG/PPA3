"""
Name: test_svr_data_store.py
Purpose: Test to make sure the GIS data store for PPA3 stuff on arc server loads correctly
    when tool is published as online tool


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import arcpy
import pandas as pd




if __name__ == '__main__':
    csv_in = r"\\arcserver-svr\D\PPA3_SVR\RegionalProgram\CSV\Agg_ppa_vals04222020_1017.csv"

    df = pd.read_csv(csv_in)
    rowcnt = df.shape[0]
    out_str = f"CSV loaded successfully; {rowcnt} rows in dataframe."

    arcpy.AddMessage(out_str)