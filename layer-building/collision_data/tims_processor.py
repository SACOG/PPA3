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

import geopandas as gpd

@dataclass
class Dataset:
    in_csv: str

    f_case_id: str = 'CASE_ID'
    f_colln_year: str = 'ACCIDENT_YEAR'
    f_x_tims: str = 'POINT_X'
    f_y_tims: str = 'POINT_Y'
    f_x_chp: str = 'LONGITUDE'
    f_y_chp: str = 'LATITUDE'

    def __post_init__(self):
        pass

    def data_quality_summary(self):
        """generate data quality report of input data:
            -pct with 'good' X/Y values from TIMS
            -pct with 'bad' X/Y values from CHP that were truncated
            -pct with null/zero X/Y values
        """


    def load_data(self):
        # loads CSV of collision data to geopandas geodataframe
        pass





if __name__ == '__main__':
    