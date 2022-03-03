"""
Name: chart_congestion.py
Purpose: Make PPA congestion charts:
    -congested vs. free-flow speed by directoin
    -TT reliability ratio by period by direction
    -congestion ratio by direction (congested speed / free-flow speed)


Author: Darren Conly
Last Updated: Mar 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from utils import utils
import npmrds_data_conflation as npmrds





if __name__ == '__main__':
    test_out_data = {'SOUTHBOUND_calc_len': 22360.509479063476, 'SOUTHBOUNDff_speed': 28.782254523148556, 
                    'SOUTHBOUNDhavg_spd_worst4hrs': 15.09797348578854, 'SOUTHBOUNDlottr_ampk': 1.4236296182664292, 
                    'SOUTHBOUNDlottr_midday': 1.4262906792112078, 'SOUTHBOUNDlottr_pmpk': 1.4493969231449726, 
                    'SOUTHBOUNDlottr_wknd': 1.4449589790447237, 'NORTHBOUND_calc_len': 22360.50947804221, 
                    'NORTHBOUNDff_speed': 29.12001830253997, 'NORTHBOUNDhavg_spd_worst4hrs': 14.16274182912327, 
                    'NORTHBOUNDlottr_ampk': 1.3784194466762407, 'NORTHBOUNDlottr_midday': 1.376488458887411, 
                    'NORTHBOUNDlottr_pmpk': 1.4757900890316429, 'NORTHBOUNDlottr_wknd': 1.409099597539259}