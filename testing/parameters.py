"""
Name: parameters.py
Purpose: Stores all input parameter values for SACOG Project Performance Assessment Tool v3,
    for the REGIONAL PROGRAM templates and reports
        
          
Author: Darren Conly
Last Updated: Aug 2022
Updated by: <name>
Copyright:   (c) SACOG
Python Version: 3.x
"""
import os
from arcpy import env

# ========================================INPUT DATA LAYERS===================================================== 
server_folder = r'\\arcserver-svr\D\PPA3_SVR'
program_folder_name = 'RegionalProgram' # 'CommunityDesign'

program_folder = os.path.join(server_folder, program_folder_name)
fgdb = os.path.join(r"\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\owner_PPA.sde") # NEEDS UPDATE FOR PPA3
projexn_wkid_sacog = 2226 # NAD 1983 StatePlane California II FIPS 0402 (US Feet)

# -------input feature classes, all in fgdb
# region_fc = 'sacog_region'
# fc_speed_data = 'npmrds_metrics_v8' #npmrds speed data
# accdata_fc = 'Sugar_access_data_latest' # sugar accessibility polygon data
# collisions_fc = 'collisions_tims_2015_2019_fwytag' # collision point data
# trn_svc_fc = 'transit_stopcount_2019' # transit stop event data; point file
# freight_route_fc = 'STAATruckRoutes' # STAA truck route lines
# intersections_base_fc = 'intersections_2021'
comm_types_fc = 'comm_type_jurspec_dissolve'

reg_centerline_fc = 'RegionalCenterline_Oct2021'
reg_artcollcline_fc = 'OSM_ArterialCollector_2022' # 'ArterialCollector_2019' # road centerlines but for collectors and above (no local streets/alleys)

reg_bikeway_fc = 'BikeRte_C1_C2_C4_2022' # 'BikeRte_C1_C2_C4_2017'

proj_line_template_fc = 'Project_Line_Template' # has symbology that the project line will use.


# tables that results will be logged to--critical for making roll-ups and analyzing past project results
log_fgdb = r"\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb"
pickle_uid = os.path.join(env.scratchGDB, "project_uid.pkl") # pickle file containing integer unique ID that will be used for all tables
logtbl_join_key = 'project_uid' # join key field that will be shared across all tables and enable joining
log_master = 'project_master'
log_artexp_sgr = 'rp_artexp_sgr'
log_rp_artexp_vmt = 'rp_artexp_vmt'


# layers with multiple potential year values (e.g. base, various future years, etc)
base_year = 2020
future_year = 2035

def parcel_pt_fc_yr(in_year=base_year):
    return "parcel_data_pts_{}".format(in_year)


def parcel_poly_fc_yr(in_year=base_year):
    return "parcel_data_polys_{}".format(in_year)


def model_links_fc(in_year=base_year):
    return "model_links_{}".format(in_year)


# input CSV of community type and regional values for indicated metrics; used to compare how project scores compared to 
# "typical" values for the region and for the community type in which the project lies.
aggval_csv = os.path.join(program_folder, r"CSV\Agg_ppa_vals20220829_1258.csv")


# project type
ptype_fwy = 'Freeway Expansion'
ptype_arterial = 'Arterial or Transit Expansion'
ptype_sgr = 'Complete Street or State of Good Repair'
ptype_commdesign = "Community Design"
ptype_area_agg = 'AreaAvg' # e.g., regional average, community type avg

# ===================================OUTPUT APRX TEMPLATE DATA=========================================================

# params related to inserting maps into report
aprx_path = os.path.join(server_folder, r"PPA3_GIS_SVR\PPA3_GIS_SVR.aprx") # 8/30/2022: USE THIS PATH ONCE ARCSERVER UPDATE COMPLETE ON ARCSERVERGIS-SVR MACHINE
mapimg_configs_csv = os.path.join(program_folder, r"CSV\map_img_config.csv") # configs for making maps imgs
map_placement_csv = os.path.join(program_folder, r"CSV\map_report_key.csv") # configs for inserting maps into Excel reports
map_img_format = "png" #jpg, png, svg, etc.

# root url, used for map images
# FYI, it's represented as a list item instead of a string because Arc Pro gives an error 00068 if it's represented as a string.
svc_root_url = ['https://services.sacog.org/hosting/rest/directories/arcgisjobs'] 

# ===================================OUTPUT JSON TEMPLATE DATA=========================================================
json_templates_dir = os.path.join(program_folder, "JSON")

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
ann_factor = 320 # multiplier to get approximate annual value based on "typical weekday"
# ===================================ACCESSIBILITY PARAMETERS=========================================================

# # Accessibility columns
# col_geoid = "bgid"
# col_acc_ej_ind = "PPA_EJ2018"
# col_pop = "population"

# col_walk_alljob = 'WALKDESTSalljob'
# col_bike_alljob = 'BIKEDESTSalljob'
# col_drive_alljob = 'AUTODESTSalljob'
# col_transit_alljob = 'TRANDESTSalljob'
# col_walk_lowincjob = 'WALKDESTSlowjobs'
# col_bike_lowincjob = 'BIKEDESTSlowjobs'
# col_drive_lowincjob = 'AUTODESTSlowjobs'
# col_transit_lowincjob = 'TRANDESTSlowjob'
# col_walk_edu = 'WALKDESTSedu'
# col_bike_edu = 'BIKEDESTSedu'
# col_drive_edu = 'AUTODESTSedu'
# col_transit_edu = 'TRANDESTSedu'
# col_walk_poi = 'WALKDESTSpoi2'
# col_bike_poi = 'BIKEDESTSpoi2'
# col_drive_poi = 'AUTODESTSpoi2'
# col_transit_poi = 'TRANDESTSpoi2'

# acc_cols = [col_walk_alljob, col_bike_alljob, col_drive_alljob, col_transit_alljob, col_walk_edu, col_bike_edu,
#             col_drive_edu, col_transit_edu, col_walk_poi, col_bike_poi, col_drive_poi, col_transit_poi]

# acc_cols_ej = [col_walk_alljob, col_bike_alljob, col_drive_alljob, col_transit_alljob, col_walk_lowincjob,
#                col_bike_lowincjob, col_drive_lowincjob, col_transit_lowincjob, col_walk_edu, col_bike_edu,
#                col_drive_edu, col_transit_edu, col_walk_poi, col_bike_poi, col_drive_poi, col_transit_poi]



bg_search_dist = 300 # feet away from project line that you'll tag block groups in

# ===================================PROBE-BASED SPEED DATA (E.G. NPMRDS) PARAMETERS================================

# # speed data attributes
# col_ff_speed = "ff_speed"
# col_congest_speed = "havg_spd_worst4hrs"
# col_reliab_ampk = "lottr_ampk"
# col_reliab_md = "lottr_midday"
# col_reliab_pmpk = "lottr_pmpk"
# col_reliab_wknd = "lottr_wknd"
# col_tmcdir = "direction_signd"
# col_roadtype = "f_system"  # indicates if road is freeway or not, so that data from freeways doesn't affect data on surface streets, and vice-versa

# calc_distwt_avg = "distance_weighted_avg"
# calc_inv_avg = "inv_avg_spd"

# # specify the type of calculation for each field in order to aggregate to project line
# spd_data_calc_dict = {col_ff_speed: calc_inv_avg,
#                       col_congest_speed: calc_inv_avg,
#                       col_reliab_ampk: calc_distwt_avg,
#                       col_reliab_md: calc_distwt_avg,
#                       col_reliab_pmpk: calc_distwt_avg,
#                       col_reliab_wknd: calc_distwt_avg}

# col_truckpct = "Trk_Veh_Pc"
# truck_data_calc_dict = {col_truckpct: calc_distwt_avg}

# roadtypes_fwy = (1, 2)  # road type values corresponding to freeways
# directions_tmc = ["NORTHBOUND", "SOUTHBOUND", "EASTBOUND", "WESTBOUND"]

# tmc_select_srchdist = 300 # units in feet. will select TMCs within this distance of project line for analysis.
# tmc_buff_dist_ft = 90  # buffer distance, in feet, around the TMCs

# ===================================MODEL-BASED LAND USE  PARAMETERS==============================================

# # parameters for mix index
# import pandas as pd

# # input columns for land use mix calculation--MUST MATCH COLNAMES IN mix_idx_params_csv
# col_parcelid = 'PARCELID'
# col_hh = 'HH_hh'
# col_emptot = 'EMPTOT'
# col_empfood = 'EMPFOOD'
# col_empret = 'EMPRET'
# col_empsvc = 'EMPSVC'
# col_k12_enr = 'ENR_K12'

# mix_index_buffdist = 5280 #feet, default = 5280
# du_mix_buffdist = 5280 #feet, default = 5280
# ilut_sum_buffdist = 2640 # feet, default = 2640 (0.5mi)

# # park acreage info,
# col_area_ac = 'GISAc'
# col_lutype = 'LUTYPE'
# col_housing_type = 'TYPCODE_DESC'
# lutype_parks = 'Park and/or Open Space'
# col_parkac = 'PARK_AC'  # will be calc'd as GISAc if LUTYPE = park/open space LUTYPE
# park_calc_dict = {'area_field': col_area_ac,
#                   'lutype_field': col_lutype,
#                   'park_lutype': lutype_parks,
#                   'park_acres_field': col_parkac}

# lutype_ag = 'Agriculture' #from LUTYPE colume for ILUT table

# mix_idx_col = 'mix_index'

# # by default, bal_ratio_per_hh = ratio of that land use factor per HH at the regional level, and represents "ideal" ratio
# mix_calc_cols = ['lu_fac', 'bal_ratio_per_hh', 'weight']
# mix_calc_vals = [[col_k12_enr, 0.392079056, 0.2],
#              [col_empret, 0.148253453, 0.4],
#              [col_emptot, 1.085980023, 0.05],
#              [col_empsvc, 0.133409274, 0.1],
#              [col_empfood, 0.097047321, 0.2],
#              [col_parkac, 0.269931832, 0.05]
#              ]

# params_df = pd.DataFrame(mix_calc_vals, columns = mix_calc_cols) \
#     .set_index(mix_calc_cols[0])

# # ---------parameters for summary land use data ---------------------

# # other ILUT columns used
# col_pop_ilut = 'POP_TOT'
# col_ej_ind = "EJ_AREA"
# col_empind = 'EMPIND'
# col_du = 'DU_TOT'

# col_persntrip_res = 'PT_TOT_RES'
# col_sovtrip_res = 'SOV_TOT_RES'
# col_hovtrip_res = 'HOV_TOT_RES'
# col_trntrip_res = 'TRN_TOT_RES'
# col_biketrip_res = 'BIK_TOT_RES'
# col_walktrip_res = 'WLK_TOT_RES'
# ilut_ptrip_mode_fields = [col_sovtrip_res, col_hovtrip_res, col_trntrip_res, col_biketrip_res, col_walktrip_res]



# ===================================MODEL NETWORK PARAMETERS==============================================

modlink_searchdist = 700 # in feet, might have projection-related issues in online tool--how was this resolved in PPA1?

# model freeway capclasses: general purp lanes, aux lanes, HOV lanes, HOV connectors, on-off ramps, HOV ramps, freeway-freeway connector ramps
col_capclass = "CAPCLASS"

capclasses_fwy = (1, 8, 51, 56) # freeway gen purpose, aux, and HOV lanes
capclasses_ramps = (6, 16, 18, 26, 36, 46) # onramps, offramps, freeway-freeway connectors, HOV onramp meter byp lanes, metered onramp lanes
capclass_arterials = (2, 3, 4, 5, 12, 22, 24)
capclasses_nonroad = (7, 62, 63, 99)

# col_lanemi = 'LANEMI'
# col_distance = 'DISTANCE'
# col_dayvmt = 'DAYVMT'
# col_daycvmt = 'DAYCVMT'
# col_tranvol = 'TOT_TRNVOL'
# col_dayvehvol = 'DYV'
# col_sovvol = 'DYV_DA'
# col_hov2vol = 'DYV_SD2'
# col_hov3vol = 'DYV_SD3'
# col_daycommvehvol = 'DYV_CV'

# occupancy factors for shared vehicles
fac_hov2 = 2 # HOV2 = 2 people per veh
fac_hov3 = 1/0.3 # inverse of 0.3, which is factor for converting HOV3+ person trips into vehicle trips


# ============================COLLISION DATA PARAMETERS===========================
col_fwytag = "FwyTag"
ind_fwytag_fwy = 1
ind_fwytag_art = 2

# col_nkilled = "NUMBER_KILLED"
# col_bike_ind = 'BICYCLE_ACCIDENT'
# col_ped_ind = 'PEDESTRIAN_ACCIDENT'

ind_val_true = 'Y'

tags_ptypes = {ptype_fwy:'_fwy', ptype_arterial:'_nonfwy', ptype_sgr:'_nonfwy'}

colln_searchdist = 75 # in feet, might have projection-related issues in online tool-how was this resolved in PPA1?
years_of_collndata = 5

# ============================TRANSIT SERVICE DENSITY PARAMETERS===========================
trn_buff_dist = 1320 # feet, search distance for transit stops from project line
col_transit_events = "tripcnt_day" #if transit feature class is point file dissolved by stop location, this
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

col_intxn_lnks = 'LINKS'

# ============================URBANIZATION PARAMETERS===========================

# params for determining if project is in greenfield or infill area
col_ctype_old = 'comm_type'  # base ctype field, but doesn't distinguish by jurisdiction (e.g. center/corridor in dowtown sac vs in rural main street)
col_ctype = 'comm_type_ppa'  # ctype field used in jurisdiction-specific ctypes layer (e.g. rural main streets vs. downtown core)
ctypes_infill = ['Established Communities', 'Arterials & Suburban Corridors', 'Rural & Small Town Main Street',
                 'Small-Town Established Communities', 'Urban core']
threshold_val = 0.9  # if more than 90% of project length is in greenfield, then project is greenfield vice-versa for infill

# for measuring loss in acres of natural resources within project area (nat resources = forest, parks, ag land)
buff_nat_resources = 2640 #feet. Is area of consideration when measuring acres of natural resources lost within project area.


# =============================JSON CONFIG PARAMETERS FROM USER INTERFACE===============

class projInputKeys:
    """Input key values for JSON object representing configuration parameters
    from user interface"""
    def __init__(self):
        self.geom = "Project_Line"
        self.name = 'Project_Name'
        self.jur = 'Jurisdiction'
        self.adt = 'Project_ADT'
        self.aadt = 'AADT'
        self.posted_spd = 'Posted_Speed_Limit'
        self.pci = 'PCI'
        self.proj_pci = 'Project_PCI'
        self.email = 'userEmail'
        self.fmt = 'f'

# """
# EXAMPLE INPUT JSON OBJECT

# {
#     "Project_Line": {
#         "geometryType": "esriGeometryPolyline",
#         "sr": {
#             "wkid": 102642
#         },
#         "features": [
#             {
#                 "geometry": {
#                     "spatialReference": {
#                         "wkid": 102642
#                     },
#                     "paths": [
#                         [
#                             [
#                                 6748148.653240821,
#                                 2003155.4099492875
#                             ],
#                             [
#                                 6745985.7408012925,
#                                 2000534.0577610424
#                             ],
#                             [
#                                 6744517.244861613,
#                                 2000591.358323832
#                             ],
#                             [
#                                 6744483.218642788,
#                                 2002526.948155975
#                             ]
#                         ]
#                     ]
#                 }
#             }
#         ]
#     },
#     "Project_Name": "test_project",
#     "Jurisdiction": "example_jurisdiction",
#     "Project_ADT":1000,
#     "AADT": 1000,
#     "Posted_Speed_Limit":35,
#     "PCI":35,
#     "Project_PCI":35,
#     "userEmail":"fake@email.com",
#     "f":"json"
#   }

# """
