# --------------------------------
# Name: complete_street_score.py
# Purpose: Calculate complete street index (CSI) for project, which is proxy 
#       to describe how beneficial complete streets treatments would be for the project segment.
#
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
# --------------------------------
import datetime as dt
import os

import arcpy
import geopandas as gpd
import pandas as pd
from shapely import wkt as shapely_wkt
arcpy.env.overwriteOutput = True

import csi_params as params
import landuse_buff_calcs_geopandas as lubuff
import transit_svc_measure_geopandas as ts
from pandas_memory_optimization import memory_optimization


# clean this up later
lu_fac_cols = [params.col_area_ac, params.col_k12_enr, params.col_emptot, params.col_du]
lu_vals_cols = [params.col_k12_enr, params.col_emptot, params.col_du]
    
def complete_streets_idx(gdf_pclpt, gdf_project, project_type, posted_speedlim, gdf_transit_event):
    '''Calculate complete street index (CSI) for project
        CSI = (students/acre + daily transit vehicle stops/acre + BY jobs/acre + BY du/acre) * (1-(posted speed limit - threshold speed limit)*speed penalty factor)
        ''' 
    
    # don't give complete street score for freeway projects or if sponsor didn't enter speed limit
    if project_type == params.ptype_fwy or posted_speedlim <= 1: 
        csi = -1
    else:
        # arcpy.AddMessage("Calculating complete street score...")
    
        # get transit service density around project
        tran_stops_dict = ts.transit_svc_density(gdf_project, gdf_transit_event, project_type)
        transit_svc_density = list(tran_stops_dict.values())[0]
    
        # get sums of the lu_fac_cols within project buffer area
        lu_vals_obj = lubuff.LandUseBuffCalcs(gdf_pclpt, gdf_project, project_type, lu_fac_cols, params.cs_buffdist)
        lu_vals_dict = lu_vals_obj.point_sum()
    
        #dens_score = (student_dens + trn_svc_dens + job_dens + du_dens)
        if lu_vals_dict[params.col_area_ac] == 0:
            dens_score = 0
        else:
            dens_score = sum([lu_vals_dict[i] / lu_vals_dict[params.col_area_ac] for i in lu_vals_cols]) + transit_svc_density
    
        csi = dens_score * (1 - (posted_speedlim - params.cs_threshold_speed) * params.cs_spd_pen_fac)
    out_dict = {'complete_street_score': csi}
    
    return out_dict


def load_efficient_dbf(in_fc, cols):
    if 'geometry' not in cols:
        cols.append('geometry')
    # import pdb; pdb.set_trace()
    gdf = gpd.GeoDataFrame.from_file(params.fgdb, layer=in_fc, 
            driver="OpenFileGDB")[cols]

    memory_optimization(gdf)

    return gdf

def make_fc_with_csi(network_fc, transit_event_fc, fc_pclpt, project_type):
    start_time = dt.datetime.now()

    fld_oid = "OBJECTID"
    fld_geom = "SHAPE@"
    fld_strtname = "FULLSTREET"
    fld_spd = "SPEED"
    fld_len = "SHAPE@LENGTH"
    fld_csi = "CompltStreetIdx"

    # make the parcel point geodataframe
    arcpy.AddMessage("loading land use data...")
    gdf_parcels = load_efficient_dbf(fc_pclpt, cols=lu_fac_cols)

    # make the transit stop point geodataframe
    arcpy.AddMessage("loading transit stop event data...")
    gdf_transit = load_efficient_dbf(transit_event_fc, cols=["COUNT_trip_id"])

    # make the output featureclass
    fields_network = [fld_geom, fld_strtname, fld_spd, fld_len, fld_oid]
    
    time_sufx = str(dt.datetime.now().strftime('%m%d%Y%H%M'))
    output_fc = "CompleteStreetMap{}".format(time_sufx)
    
    arcpy.CreateFeatureclass_management(arcpy.env.workspace, output_fc, "POLYLINE", spatial_reference=2226)
    
    arcpy.AddField_management(output_fc, fld_strtname, "TEXT")
    arcpy.AddField_management(output_fc, fld_spd, "SHORT")
    arcpy.AddField_management(output_fc, fld_csi, "FLOAT")
    
    
    fl_network = "fl_network"
    if arcpy.Exists(fl_network): arcpy.Delete_management(fl_network)
    arcpy.MakeFeatureLayer_management(network_fc, fl_network)

    total_net_links = arcpy.GetCount_management(fl_network)[0]
    
    print(f"inserting rows, starting at {start_time}...")
    with arcpy.da.InsertCursor(output_fc, [fld_geom, fld_strtname, fld_spd, fld_csi]) as inscur:
        with arcpy.da.SearchCursor(fl_network, fields_network) as cur:
            for i, row in enumerate(cur):
                if i % 1000 == 0:
                    st_time = dt.datetime.now() - start_time
                    print(f"{i} out of {total_net_links} rows processed, with {st_time} elapsed.")
                geom = row[0]
                stname = row[1]
                speedlim = row[2]
                
                # import pdb; pdb.set_trace()
                dft = pd.DataFrame([geom.WKT], columns=['geometry_wkt'])
                dft['geometry'] = dft['geometry_wkt'].apply(shapely_wkt.loads)
                project_gdf = gpd.GeoDataFrame(dft, geometry='geometry')
                
                csi_dict = complete_streets_idx(gdf_parcels, project_gdf, project_type, speedlim, gdf_transit)
                csi = csi_dict['complete_street_score']

                ins_row = [geom, stname, speedlim, csi]
                inscur.insertRow(ins_row)
    time_elapsed = dt.datetime.now() - start_time
    print("Finished! Processed {} rows in {}".format(i + 1, time_elapsed))

    output_path = os.path.join(arcpy.env.workspace, output_fc)
    print(f"Output feature class in {output_path}")


if __name__ == '__main__':
    arcpy.env.workspace = r"C:\\PPA_CS_batch_temp\\TEMP_PPA_cs_data.gdb"

    # input fc of parcel data--must be points!
    # PERFORMANCE TIP - parcel fc should only have parcel points within desired buffer distance of roads, rather than all parcels in region.
    in_pcl_pt_fc = 'parcel_data_pts_2016_qmi_roads' # params.parcel_pt_fc_yr(in_year=2016) # "parcel_data_pts_SAMPLE" 
    value_fields = [params.col_area_ac, params.col_k12_enr, params.col_emptot, params.col_du]
    ptype = 'Arterial'

    # input line project for basing spatial selection
    # NOTE - input files should come from local drive in case network connections fail
    input_network_fc = 'Centerline_ArterialCollector10132021' # 'TestCenterlinesEastSac'
    # trnstops_fc = os.path.join(params.fgdb, params.trn_svc_fc)
    trnstops_fc = params.trn_svc_fc

    make_fc_with_csi(input_network_fc, trnstops_fc, in_pcl_pt_fc, ptype)
    

