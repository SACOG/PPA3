"""
Name: parameters.py
Purpose: Stores all input parameter values for SACOG Project Performance Assessment Tool v3,
    for the REGIONAL PROGRAM templates and reports
        
          
Author: Darren Conly
Last Updated: Mar 2022
Updated by: <name>
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os

# ========================================INPUT DATA LAYERS===================================================== 
server_folder = r'\\arcserver-svr\D\PPA3_SVR\RegionalProgram'


fgdb = os.path.join(r"\\arcserver-svr\D\PPA_v2_SVR\PPA2_GIS_SVR\owner_PPA.sde") # NEEDS UPDATE FOR PPA3
projexn_wkid_sacog = 2226 # NAD 1983 StatePlane California II FIPS 0402 (US Feet)

# -------input feature classes, all in fgdb
region_fc = 'sacog_region'
fc_speed_data = 'npmrds_metrics_v8' #npmrds speed data
accdata_fc = 'Sugar_access_data_latest' # sugar accessibility polygon data
collisions_fc = 'Collisions2014to2018fwytag' # collision point data
trn_svc_fc = 'transit_stoplocn_w_eventcount_2016' # transit stop event data; point file
freight_route_fc = 'STAATruckRoutes' # STAA truck route lines
intersections_base_fc = 'intersections_2016'
comm_types_fc = 'comm_type_jurspec_dissolve'

reg_centerline_fc = 'RegionalCenterline_2019'
reg_artcollcline_fc = 'ArterialCollector_2019' # road centerlines but for collectors and above (no local streets/alleys)

reg_bikeway_fc = 'BikeRte_C1_C2_C4_2019' # 'BikeRte_C1_C2_C4_2017'

proj_line_template_fc = 'Project_Line_Template' # has symbology that the project line will use.
all_projects_fc = "All_PPA_Projects2020" # feature class to which all run projects are added--NEED UPDATE FOR PPA3

# layers with multiple potential year values (e.g. base, various future years, etc)
def parcel_pt_fc_yr(in_year=2016):
    return "parcel_data_pts_{}".format(in_year)


def parcel_poly_fc_yr(in_year=2016):
    return "parcel_data_polys_{}".format(in_year)


def model_links_fc(in_year=2016):
    return "model_links_{}".format(in_year)


# input CSV of community type and regional values for indicated metrics; used to compare how project scores compared to 
# "typical" values for the region and for the community type in which the project lies.
aggval_csv = os.path.join(server_folder, r"CSV\Agg_ppa_vals20220829_1258.csv")


# project type
ptype_fwy = 'Freeway Expansion'
ptype_arterial = 'Arterial or Transit Expansion'
ptype_sgr = 'Complete Street or State of Good Repair'
ptype_commdesign = "Community Design"
ptype_area_agg = 'AreaAvg' # e.g., regional average, community type avg


# ===================================OUTPUT APRX TEMPLATE DATA=========================================================

# params related to inserting maps into report--WILL NEED TO UPDATE FOR PPA3
TEMP_ppa2_svr_path = r'\\arcserver-svr\D\PPA_v2_SVR'
aprx_path = os.path.join(TEMP_ppa2_svr_path, r"PPA2_GIS_SVR\PPA2_GIS_SVR_v2.aprx")
mapimg_configs_csv = os.path.join(TEMP_ppa2_svr_path, r"PPA2\Input_Template\CSV\map_img_config.csv") # configs for making maps imgs
map_placement_csv = os.path.join(TEMP_ppa2_svr_path, r"PPA2\Input_Template\CSV\map_report_key.csv") # configs for inserting maps into Excel reports
map_img_format = "png" #jpg, png, svg, etc.

# root url, used for map images
# FYI, it's represented as a list item instead of a string because Arc Pro gives an error 00068 if it's represented as a string.
svc_root_url = ['https://services.sacog.org/hosting/rest/directories/arcgisjobs'] 

# ===================================OUTPUT JSON TEMPLATE DATA=========================================================
json_templates_dir = os.path.join(server_folder, "JSON")

# names in json template
geo_project = "Project"
geo_proj_qmi = "Within 0.25mi"
geo_ctype = "Community Type"
geo_region = "Region"

# re-used json keys, so assign to variable
k_charts = "charts"
k_name = "name"
k_value = "value"
k_features = "features" # remember, this is a list of dicts
k_attrs = "attributes"
k_year = "year"
k_type = "type"


# ===================================CONVERSION FACTORS=========================================================
ft2acre = 43560 # convert square feet to acres
ft2mile = 5280
# ===================================ACCESSIBILITY PARAMETERS=========================================================

# Accessibility columns
col_geoid = "bgid"
col_acc_ej_ind = "PPA_EJ2018"
col_pop = "population"

col_walk_alljob = 'WALKDESTSalljob'
col_bike_alljob = 'BIKEDESTSalljob'
col_drive_alljob = 'AUTODESTSalljob'
col_transit_alljob = 'TRANDESTSalljob'
col_walk_lowincjob = 'WALKDESTSlowjobs'
col_bike_lowincjob = 'BIKEDESTSlowjobs'
col_drive_lowincjob = 'AUTODESTSlowjobs'
col_transit_lowincjob = 'TRANDESTSlowjob'
col_walk_edu = 'WALKDESTSedu'
col_bike_edu = 'BIKEDESTSedu'
col_drive_edu = 'AUTODESTSedu'
col_transit_edu = 'TRANDESTSedu'
col_walk_poi = 'WALKDESTSpoi2'
col_bike_poi = 'BIKEDESTSpoi2'
col_drive_poi = 'AUTODESTSpoi2'
col_transit_poi = 'TRANDESTSpoi2'

acc_cols = [col_walk_alljob, col_bike_alljob, col_drive_alljob, col_transit_alljob, col_walk_edu, col_bike_edu,
            col_drive_edu, col_transit_edu, col_walk_poi, col_bike_poi, col_drive_poi, col_transit_poi]

acc_cols_ej = [col_walk_alljob, col_bike_alljob, col_drive_alljob, col_transit_alljob, col_walk_lowincjob,
               col_bike_lowincjob, col_drive_lowincjob, col_transit_lowincjob, col_walk_edu, col_bike_edu,
               col_drive_edu, col_transit_edu, col_walk_poi, col_bike_poi, col_drive_poi, col_transit_poi]



bg_search_dist = 300 # feet away from project line that you'll tag block groups in

# ===================================PROBE-BASED SPEED DATA (E.G. NPMRDS) PARAMETERS================================

# speed data attributes
col_ff_speed = "ff_speed"
col_congest_speed = "havg_spd_worst4hrs"
col_reliab_ampk = "lottr_ampk"
col_reliab_md = "lottr_midday"
col_reliab_pmpk = "lottr_pmpk"
col_reliab_wknd = "lottr_wknd"
col_tmcdir = "direction_signd"
col_roadtype = "f_system"  # indicates if road is freeway or not, so that data from freeways doesn't affect data on surface streets, and vice-versa

calc_distwt_avg = "distance_weighted_avg"
calc_inv_avg = "inv_avg_spd"

# specify the type of calculation for each field in order to aggregate to project line
spd_data_calc_dict = {col_ff_speed: calc_inv_avg,
                      col_congest_speed: calc_inv_avg,
                      col_reliab_ampk: calc_distwt_avg,
                      col_reliab_md: calc_distwt_avg,
                      col_reliab_pmpk: calc_distwt_avg,
                      col_reliab_wknd: calc_distwt_avg}

col_truckpct = "Trk_Veh_Pc"
truck_data_calc_dict = {col_truckpct: calc_distwt_avg}

roadtypes_fwy = (1, 2)  # road type values corresponding to freeways
directions_tmc = ["NORTHBOUND", "SOUTHBOUND", "EASTBOUND", "WESTBOUND"]

tmc_select_srchdist = 300 # units in feet. will select TMCs within this distance of project line for analysis.
tmc_buff_dist_ft = 90  # buffer distance, in feet, around the TMCs

# ===================================MODEL-BASED LAND USE  PARAMETERS==============================================

# parameters for mix index
import pandas as pd

# input columns for land use mix calculation--MUST MATCH COLNAMES IN mix_idx_params_csv
col_parcelid = 'PARCELID'
col_hh = 'HH_hh'
col_emptot = 'EMPTOT'
col_empfood = 'EMPFOOD'
col_empret = 'EMPRET'
col_empsvc = 'EMPSVC'
col_k12_enr = 'ENR_K12'

mix_index_buffdist = 5280 #feet, default = 5280
du_mix_buffdist = 5280 #feet, default = 5280
ilut_sum_buffdist = 2640 # feet, default = 2640 (0.5mi)


col_lutype = 'LUTYPE'
lutype_parks = 'Park and/or Open Space'
lutype_ag = 'Agriculture' #from LUTYPE colume for ILUT table

mix_idx_col = 'mix_index'


# ---------parameters for summary land use data ---------------------

# other ILUT columns used
col_pop_ilut = 'POP_TOT'
col_ej_ind = "EJ_AREA"
col_empind = 'EMPIND'
col_du = 'DU_TOT'

col_persntrip_res = 'PT_TOT_RES'
col_sovtrip_res = 'SOV_TOT_RES'
col_hovtrip_res = 'HOV_TOT_RES'
col_trntrip_res = 'TRN_TOT_RES'
col_biketrip_res = 'BIK_TOT_RES'
col_walktrip_res = 'WLK_TOT_RES'
ilut_ptrip_mode_fields = [col_sovtrip_res, col_hovtrip_res, col_trntrip_res, col_biketrip_res, col_walktrip_res]



# ===================================MODEL NETWORK PARAMETERS==============================================

modlink_searchdist = 700 # in feet, might have projection-related issues in online tool--how was this resolved in PPA1?

# model freeway capclasses: general purp lanes, aux lanes, HOV lanes, HOV connectors, on-off ramps, HOV ramps, freeway-freeway connector ramps
col_capclass = "CAPCLASS"

capclasses_fwy = (1, 8, 51, 56) # freeway gen purpose, aux, and HOV lanes
capclasses_ramps = (6, 16, 18, 26, 36, 46) # onramps, offramps, freeway-freeway connectors, HOV onramp meter byp lanes, metered onramp lanes
capclass_arterials = (2, 3, 4, 5, 12, 22, 24)
capclasses_nonroad = (7, 62, 63, 99)

col_lanemi = 'LANEMI'
col_distance = 'DISTANCE'
col_dayvmt = 'DAYVMT'
col_daycvmt = 'DAYCVMT'
col_tranvol = 'TOT_TRNVOL'
col_dayvehvol = 'DYV'
col_sovvol = 'DYV_DA'
col_hov2vol = 'DYV_SD2'
col_hov3vol = 'DYV_SD3'
col_daycommvehvol = 'DYV_CV'

# occupancy factors for shared vehicles
fac_hov2 = 2 # HOV2 = 2 people per veh
fac_hov3 = 1/0.3 # inverse of 0.3, which is factor for converting HOV3+ person trips into vehicle trips


# ============================COLLISION DATA PARAMETERS===========================
col_fwytag = "fwy_yn"
col_nkilled = "NUMBER_KILLED"
col_bike_ind = 'BICYCLE_ACCIDENT'
col_ped_ind = 'PEDESTRIAN_ACCIDENT'

ind_val_true = 'Y'

colln_searchdist = 75 # in feet, might have projection-related issues in online tool-how was this resolved in PPA1?
years_of_collndata = 5

# ============================TRANSIT SERVICE DENSITY PARAMETERS===========================
trn_buff_dist = 1320 # feet, search distance for transit stops from project line
col_transit_events = "COUNT_trip_id" #if transit feature class is point file dissolved by stop location, this
                                    #col is number of times per day that transit vehicle served each stop



# ============================COMPLETE STREETS INDEX PARAMETERS===========================

# CSI = (students/acre + daily transit vehicle stops/acre + BY jobs/acre + BY du/acre)
#                  * (1-(posted speed limit - threshold speed limit)*speed penalty factor)
# FYI, CSI WILL BE UPDATED AND NORMALIZED BASED ON REGIONAL MAX FOR PPA3

cs_buffdist = 2640 # feet
col_area_ac = 'GISAc'
cs_lu_facs = [col_area_ac, col_k12_enr, col_emptot, col_du]

cs_threshold_speed = 40 # MPH
cs_spd_pen_fac = 0.04 # speed penalty factor

intersxn_dens_buff = 1320 # distance in feet
bikeway_buff = 1320 # distance in feet

# ============================URBANIZATION PARAMETERS===========================

# params for determining if project is in greenfield or infill area
col_ctype_old = 'comm_type'  # base ctype field, but doesn't distinguish by jurisdiction (e.g. center/corridor in dowtown sac vs in rural main street)
col_ctype = 'comm_type_ppa'  # ctype field used in jurisdiction-specific ctypes layer (e.g. rural main streets vs. downtown core)
ctypes_infill = ['Established Communities', 'Arterials & Suburban Corridors', 'Rural & Small Town Main Street',
                 'Small-Town Established Communities', 'Urban core']
threshold_val = 0.9  # if more than 90% of project length is in greenfield, then project is greenfield vice-versa for infill

# for measuring loss in acres of natural resources within project area (nat resources = forest, parks, ag land)
buff_nat_resources = 2640 #feet. Is area of consideration when measuring acres of natural resources lost within project area.


