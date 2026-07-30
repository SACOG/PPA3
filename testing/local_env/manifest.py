"""Single source of truth for the shared input feature classes Tier-1 testing needs.
Names only — they resolve against the SDE (source) or PPA3Testing.gdb (local) via arcpy.env.workspace.
Derived from globalconfig_rp/data_paths.yaml (sde section) + parcel FCs from parameters.parcel_pt_fc_yr."""

SHARED_FCS = [
    "sacog_region",
    "NPMRDS_2023ppadata_final",
    "Sugar_access_data_latest",
    "Collisions2019to2023",
    "transit_activity_weekdays2024",
    "STAATruckRoutes",
    "intersections_2024",
    "comm_type_jurspec_dissolve",
    "RegionalCenterline_2024",
    "OSM_ArterialCollector_2022",
    "BikeRte_C1_C2_C4_2024",
    "Project_Line_Template",
    "parcel_data_pts_2020",
    "parcel_data_pts_2035",
    "parcel_data_polys_2020",
    "parcel_data_polys_2035",
    "model_links_2020",
    "model_links_2035",
    "TCAC_2021",
]
