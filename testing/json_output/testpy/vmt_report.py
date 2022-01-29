"""
Name:vmt_report.py
Purpose:  take output data from VMT-related functions and build VMT chart spec JSON
        
          
Author: Darren Conly
Last Updated: Jan 2022
Updated by: <name>
Copyright:   (c) SACOG
Python Version: 3.x
"""

import json

from get_aggdata import get_aggvals


# convert json file into class for each report for more flexibility in coding/parsing
class VMTReport:
    def __init__(self, in_json):
        # load json template
        self.loaded_json = self.load_json_file(in_json)
        
        # load agg (region and comm type) data table
        # NOTE - will need other function to process appropriately and get ones specific to each metric
        self.agg_data_csv = agg_data_csv

        # attributes of all charts
        self.k_charts = 'charts'
        self.chart_features = 'features'
        self.chart_attrs = 'attributes'
        self.type = 'type'

        # regional and community type lookup table geography names
        self.aggdata_ctype = 'CommunityType'
        self.aggdata_regn = 'REGION'
        
        # JSON names for each geography
        self.geo_proj = 'Project'
        self.geo_ctyp = 'Community Type'
        self.geo_regn = 'Region'
        
        self.geogs_list = [self.geo_proj, self.geo_ctyp, self.geo_regn]
        


        # accessibility chart
    
    def load_json_file(self, in_json_file):
        with open(in_json_file, "r") as j_in:
            return json.load(j_in)
        
    def emp_du_chart(self, data=None):
        # chart label keys
        self.chart_jdu = 'Jobs and Dwelling'
        self.label_jobs = 'jobs'
        self.label_du = 'dwellingUnits'
        self.label_year = 'year'
        
        # keys in dict of output data
        self.d_year = 'year'
        self.d_emp = 'EMPTOT'
        self.d_du = 'DU_TOT'
            
        data_keys_list = list(data.keys())
        for i, year in enumerate(data_keys_list):
            # update json values
            
            update_dict = {self.label_year:str(year), 
                           self.label_jobs:data[year][self.d_emp],
                           self.label_du:data[year][self.d_du]
                          }
                
            for lname, val in update_dict.items():
                self.loaded_json[self.k_charts][self.chart_jdu][self.chart_features][i] \
                    [self.chart_attrs][lname] = val
                
    def lu_diversity_chart(self, project_data, aggd_data):
        ###NEEDS TO HAVE REGION AND COMMUNITY TYPE STUFF PUT IN!###
        ### MAYBE CAN HAVE SEPARATE FUNCTION THAT JUST INSERTS AGG AVGS???
        # chart label keys
        self.chart_land_div = 'Land Use Diversity'
        self.label_div_prefix = 'diversity '
        
        # project data keys
        self.d_mixidx = 'mix_index'
        year_data_keys = list(project_data.keys())
        
        # comm type and region data keys
        # aggd_data_keylist = list(aggd_data.keys())
        
        for i, geo_type in enumerate(self.geogs_list):
            update_dict = {self.type: geo_type}
            
            for k, year in enumerate(year_data_keys):
                geo_typdict = {self.geo_proj:project_data[year][self.d_mixidx], 
                     self.geo_ctyp:aggd_data[year][self.aggdata_ctype], 
                     self.geo_regn:aggd_data[year][self.aggdata_regn]}
                
                update_dict[f"{self.label_div_prefix}{year}"] = geo_typdict[geo_type]
            
            # import pdb; pdb.set_trace()
            self.loaded_json[self.k_charts][self.chart_land_div][self.chart_features][i] \
            [self.chart_attrs] = update_dict
            
    def accessibility_chart(self, project_data, aggd_data):
        # each "feature" is an accessibility type
        # each type also has project, ctype, region labels.
        
        self.chart_accsvcs = 'Base Year Service Accessibility'
        
        #{name from data set: name in VGIS json file}
        self.names_dict = {'WALKDESTSpoi2':'30 Min Walk', 
                                'BIKEDESTSpoi2':'30 Min Biking', 
                                'AUTODESTSpoi2':'15 Min Drive', 
                                'TRANDESTSpoi2':'45 Min Transit'}
        
        acc_data_keys = list(self.names_dict.keys())
        
        agg_data_scenarios = [2016] # not really used right now, but building in case we 
        # eventually do before-after accessibility comparison
        
        for i, acctype in enumerate(acc_data_keys):
            update_dict = {self.type:self.names_dict[acctype]} # type
            agg_acc_dict = aggd_data[i][acctype] # dict with acc type, year, commtype value, reg value
            # import pdb; pdb.set_trace()
            
            for scen in agg_data_scenarios:            
                update_dict[self.geo_proj] = project_data[acctype] # project's acc value
                update_dict[self.geo_ctyp] = agg_acc_dict[scen][self.aggdata_ctype]
                update_dict[self.geo_regn] = agg_acc_dict[scen][self.aggdata_regn]
            
            self.loaded_json[self.k_charts][self.chart_accsvcs][self.chart_features][i] \
            [self.chart_attrs] = update_dict
            
                
            
        
if __name__ == '__main__':
    in_json = r"C:\Users\dconly\GitRepos\PPA3\testing\json_output\SACOG_ReduceVMT_template.json"

    to = VMTReport(in_json)
    to.emp_du_chart(lubuff_output)
    to.lu_diversity_chart(project_data=lu_divers_output, aggd_data=lu_div_agg_output)
    to.accessibility_chart(project_data=acc_project_data, aggd_data=acc_agg_data)