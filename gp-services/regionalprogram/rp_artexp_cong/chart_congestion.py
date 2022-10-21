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
import re
import json

import parameters as params


class CongestionReport(object):
    def __init__(self, in_data, json_template):
        self.raw_data = in_data # python dictionary, output of separate script that gets speed data/reliability data
        self.json_template = json_template # JSON python object, not a JSON file path

        self.data_dir_names = params.directions_tmc
        self.chart_dir_names = ['NB', 'SB', 'EB', 'WB']
        self.dirname_dict = dict(zip(self.data_dir_names, self.chart_dir_names))
        self.directions_used = self.get_unique_directions()

        # tags in the raw data that indicate metric type
        self.ffs = 'ff_speed'
        self.congspd = 'havg_spd_worst4hrs'
        self.lottrampk = 'lottr_ampk'
        self.lottrpmpk = 'lottr_pmpk'
        self.lottrmd = 'lottr_midday'
        self.lottrwknd = 'lottr_wknd'

        self.congtags = [self.ffs, self.congspd]
        self.lottrtags = [self.ffs, self.congspd, self.lottrampk, self.lottrpmpk, self.lottrmd, self.lottrwknd]


        # tags taken from JSON file that are unique to the congestion/reliability charts
        self.cong_chart_title = "Free flow vs Congested Speeds"
        self.tag_ffs = "freeFlowSpeed"
        self.tag_congspd = "averageCongestedSpeed"
        self.tag_congratio = 'congestionRatio'

        # lottr JSON tags
        self.ttr_chart_title = "Travel Time Reliability Index"
        self.tag_ampk = 'AMPeak'
        self.tag_pmpk = 'PMPeak'
        self.tag_md = 'midday'
        self.tag_weekend = 'weekend'

    def get_unique_directions(self):
        # get the direction names for the currently consider projects
        out_list = []
        for k in self.raw_data.keys():
            for dirname in self.data_dir_names:
                if re.match(dirname, k): out_list.append(dirname)

        out_list_unique = list(set(out_list))

        return out_list_unique

    def parse_congestion(self):
        # output dict: {direction: {key: congstion speed value}}
        out_dict = {}
        for direcn in self.directions_used:
            data_dirn = {k.split(direcn)[1]:v for k, v in self.raw_data.items() if re.match(direcn, k)} # e.g. {'SOUTHBOUNDffs': 99, ...}
            dir_subdict = {k:v for k, v in data_dirn.items() if k in self.congtags} # return only data for free-flow speed and congested speed

            # add congestion ratio as a dict entry
            congratio = 0 if dir_subdict[self.ffs] == 0 \
                else dir_subdict[self.congspd] / dir_subdict[self.ffs]
            dir_subdict[self.tag_congratio] =  congratio

            out_dict[direcn] = dir_subdict
        
        return out_dict


    def parse_reliability(self):
        # output dict: {direction: {key: lottr value}}
        out_dict = {}
        for direcn in self.directions_used:
            data_dirn = {k.split(direcn)[1]:v for k, v in self.raw_data.items() if re.match(direcn, k)} # e.g. {'SOUTHBOUNDffs': 99, ...}
            dir_subdict = {k:v for k, v in data_dirn.items() if k in self.lottrtags} # return only data for free-flow speed and congested speed

            out_dict[direcn] = dir_subdict
        
        return out_dict

    def get_chart_dirname(self, data, dir_keyval):
        # for one-way streets, will only have values for one direction. For the "other"
        # non-existent direction, all values are zero and the direction name in chart should show up as "Null"
        
        sum_dirvals = sum(data[dir_keyval].values())
        out_dirname = 'Null' if sum_dirvals == 0 else self.dirname_dict[dir_keyval]
        
        return out_dirname

    def update_cong_chart(self):
        # update chart of congested and free-flow speeds
        update_data = self.parse_congestion()
        for i, direcn in enumerate(sorted(update_data.keys())): # ensure that x axis labels are in consistent order across reports
            chart_dirname = self.get_chart_dirname(update_data, direcn)
            self.json_template[params.k_charts][self.cong_chart_title][params.k_features][i] \
                [params.k_attrs][params.k_type] = chart_dirname
            self.json_template[params.k_charts][self.cong_chart_title][params.k_features][i] \
                [params.k_attrs][self.tag_ffs] = update_data[direcn][self.ffs]
            self.json_template[params.k_charts][self.cong_chart_title][params.k_features][i] \
                [params.k_attrs][self.tag_congspd] = update_data[direcn][self.congspd]
        
        return self.json_template
    
    def update_ttr_chart(self):
        # update chart of travel time reliability
        update_data = self.parse_reliability()
        for i, direcn in enumerate(sorted(update_data.keys())): # ensure that x axis labels are in consistent order across reports
            chart_dirname = self.get_chart_dirname(update_data, direcn) # example: 'SOUTHBOUND' becomes 'SB'
            self.json_template[params.k_charts][self.ttr_chart_title][params.k_features][i] \
                [params.k_attrs][params.k_type] = chart_dirname
            self.json_template[params.k_charts][self.ttr_chart_title][params.k_features][i] \
                [params.k_attrs][self.tag_ampk] = update_data[direcn][self.lottrampk]
            self.json_template[params.k_charts][self.ttr_chart_title][params.k_features][i] \
                [params.k_attrs][self.tag_pmpk] = update_data[direcn][self.lottrpmpk]
            self.json_template[params.k_charts][self.ttr_chart_title][params.k_features][i] \
                [params.k_attrs][self.tag_md] = update_data[direcn][self.lottrmd]
            self.json_template[params.k_charts][self.ttr_chart_title][params.k_features][i] \
                [params.k_attrs][self.tag_weekend] = update_data[direcn][self.lottrwknd]

        return self.json_template

    def update_cong_ratio(self):
        # update table of congestion ratio for each direction
        update_data = self.parse_congestion()

        secn_keys = list(self.json_template[self.tag_congratio].keys())
        direcn_keys = list(sorted(update_data.keys()))
        keys_dict = dict(zip(direcn_keys, secn_keys))

        for direcn, secn_key in keys_dict.items():
            chart_dirname = self.get_chart_dirname(update_data, direcn) # example: 'SOUTHBOUND' becomes 'SB' 
            self.json_template[self.tag_congratio][secn_key][params.k_name] = chart_dirname
            self.json_template[self.tag_congratio][secn_key][params.k_value] = update_data[direcn][self.tag_congratio]

    def update_all_congestion_data(self):
        self.update_cong_chart()
        self.update_ttr_chart()
        self.update_cong_ratio()

        # return self.json_template


if __name__ == '__main__':
    test_out_data = {'SOUTHBOUND_calc_len': 22360.509479063476, 'SOUTHBOUNDff_speed': 28.782254523148556, 
                    'SOUTHBOUNDhavg_spd_worst4hrs': 15.09797348578854, 'SOUTHBOUNDlottr_ampk': 1.4236296182664292, 
                    'SOUTHBOUNDlottr_midday': 1.4262906792112078, 'SOUTHBOUNDlottr_pmpk': 1.4493969231449726, 
                    'SOUTHBOUNDlottr_wknd': 1.4449589790447237, 'NORTHBOUND_calc_len': 22360.50947804221, 
                    'NORTHBOUNDff_speed': 29.12001830253997, 'NORTHBOUNDhavg_spd_worst4hrs': 14.16274182912327, 
                    'NORTHBOUNDlottr_ampk': 1.3784194466762407, 'NORTHBOUNDlottr_midday': 1.376488458887411, 
                    'NORTHBOUNDlottr_pmpk': 1.4757900890316429, 'NORTHBOUNDlottr_wknd': 1.409099597539259}

    json_f = r"\\arcserver-svr\D\PPA3_SVR\RegionalProgram\JSON\SACOG_{Regional Program}_{Arterial_or_Transit_Expasion}_ReduceCongestion_sample_dataSource.json"
    with open(json_f, 'r') as f:
        j_loaded = json.load(f)

    rpt_obj = CongestionReport(test_out_data, j_loaded)
    print(rpt_obj.parse_congestion())
    print(rpt_obj.parse_reliability())
    rpt_obj.update_all_congestion_data()
    print(json.dumps(rpt_obj.json_template, indent=4))

