# Esri start of added imports
import sys, os, arcpy
import math
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = 'fl_splitprojlines'
g_ESRI_variable_2 = 'fl_splitproj_w_tmcdata'
g_ESRI_variable_3 = "{} = '{}'"
g_ESRI_variable_4 = '{} IS NOT NULL'
g_ESRI_variable_5 = os.path.join(arcpy.env.packageWorkspace,'index')
g_ESRI_variable_6 = 'fl_project'
g_ESRI_variable_7 = 'fl_speed_data'
g_ESRI_variable_8 = '{} IN {}'
g_ESRI_variable_9 = 'fl_tmc_buff'
# Esri end of added variables

'''
#--------------------------------
# Name:PPA_getNPMRDSdata.py
# Purpose: Get distance-weighted average speed from NPMRDS data for PPA project,
#          
#           
# Author: Darren Conly
# Last Updated: <date>
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: <version>
#--------------------------------

Sample projects used: CAL20466, SAC25062
'''
import os
import re
import datetime as dt

import arcpy
import pandas as pd

from config_links import params
from utils import utils as ut

arcpy.env.overwriteOutput = True

dateSuffix = str(dt.date.today().strftime('%m%d%Y'))



# ====================FUNCTIONS==========================================

def get_wtd_speed(in_df, in_field, direction, fld_pc_len_ft):
    fielddir = "{}{}".format(direction, in_field)
    
    fld_invspd = "spdinv_hpm"
    fld_pc_tt = "projpc_tt"
    fld_len_mi = "pc_len_mi"
    
    in_df[fld_invspd] = 1/in_df[in_field]  # calculate each piece's "hours per mile", or inverted speed, as 1/speed
        
    # get each piece's travel time, in hours as inverted speed (hrs per mi) * piece distance (mi)
    in_df[fld_len_mi] = in_df[fld_pc_len_ft]/params.ft2mile
    in_df[fld_pc_tt] = in_df[fld_invspd] * in_df[fld_len_mi]
        
    # get total travel time, in hours, for all pieces, then divide total distance, in miles, for all pieces by the total tt
    # to get average MPH for the project
    proj_mph = in_df[fld_len_mi].sum() / in_df[fld_pc_tt].sum()
    
    return {fielddir: proj_mph}

def compute_feature_angles(in_fc, id_field):
    def get_card_angle(start_x, start_y, end_x, end_y):
        '''Based on start and end point coordinates, calculates direction in degrees
        for traveling in straight line between start and end point'''
        xdiff = end_x - start_x
        ydiff = end_y - start_y
        angle_degrees = math.degrees(math.atan2(ydiff, xdiff))
        
        return angle_degrees

    f_geom = "SHAPE@"
    fields = [id_field, f_geom]

    results = {}
    with arcpy.da.SearchCursor(in_fc, fields) as ucur:
        for row in ucur:
            start_lat = row[fields.index(f_geom)].firstPoint.Y
            start_lon = row[fields.index(f_geom)].firstPoint.X
            end_lat = row[fields.index(f_geom)].lastPoint.Y
            end_lon = row[fields.index(f_geom)].lastPoint.X
            
            link_id = row[fields.index(id_field)]
            link_angle = get_card_angle(start_lon, start_lat, end_lon, end_lat)
            results[link_id] = link_angle

    return results

def list2qrytuple(in_list):
    # for sql "in list" clauses, correctly formats a list of values as a tuple
    # in particular if list length is zero, it removes the trailing comma that tuples have
    qry_clause = f"('{in_list[0]}')"
    if len(in_list) > 1:
        qry_clause = tuple(in_list) 

    return qry_clause  

def remove_cross_streets(fl_selected_tmcbuffs, fl_tmc_lines, project_angle):
    # intersecting_fl assumed to be subset that only contains segments that intersect
    # fl_project. Goal of this function is to further filter intersecting_fl
    # to only return fl with segments that intersect fl_project that are not cross streets

    # but how to do for multi-piece projects on multiple streets?
    # In such a case, each piece of the project maybe should run through this whole process
    # separately, then re-run the averaging methods at the very end?

    # as stopgap "lazy" fix can remove the cross-traffic *if* there is only one feature (piece).
    # this would at least fix the issue for single-piece project lines. For multi-piece it shouldn't be too big a problem
    # because either it's long enough to where cross-traffic wouldn't be an issue, or it's a project 
    # where it inherently doesn't make sense to try to get a single avg speed (e.g. project spanning multiple intersections)

    # get IDs of TMCs whose buffers intersect project line
    initial_tmc_selection = []
    with arcpy.da.SearchCursor(fl_selected_tmcbuffs, [params.col_tmc_id]) as cur:
        for row in cur: initial_tmc_selection.append(row[0])

    # filter out master TMC line features to be those whose buffers intersect project line
    qry_tmc_clause = list2qrytuple(initial_tmc_selection)
    qry = f"{params.col_tmc_id} IN {qry_tmc_clause}"
    arcpy.management.SelectLayerByAttribute(fl_tmc_lines, 'NEW_SELECTION', qry)

    # get angle of selected TMC lines
    tmc_angles = compute_feature_angles(fl_tmc_lines, id_field=params.col_tmc_id)
    
    # compare angles of selected TMCs vs. project angle. Eliminate if too different from project line (e.g., is clearly a cross street)
    tmcs_to_keep = []
    for tmc, angle in tmc_angles.items():
        angle_diff = project_angle - angle
        if abs(angle_diff) <= 10:
            tmcs_to_keep.append(tmc) # if less than 10-degree diff, is okay to continue conflating

    arcpy.management.SelectLayerByAttribute(fl_tmc_lines, 'CLEAR_SELECTION')
    return tmcs_to_keep

    

def conflate_tmc2projline(fl_proj, dirxn_list, tmc_dir_field,
                          fl_tmcs_buffd, tmc_lines, fields_calc_dict):

    speed_data_fields = [k for k, v in fields_calc_dict.items()]
    out_row_dict = {}
    
    # get length of project (sum of lengths of all project pieces)
    fld_shp_len = "SHAPE@LENGTH"
    fld_totprojlen = "proj_length_ft"
    out_row_dict[fld_totprojlen] = 0
    
    with arcpy.da.SearchCursor(fl_proj, fld_shp_len) as cur:
        for row in cur:
            out_row_dict[fld_totprojlen] += row[0]

    # if only one feature in the project, compute the angle of the project line
    # this will be used to help eliminate incorrect TMC matches for short projects
    # (e.g., a short E-W project that gets N-S congestion data wrongly tagged to it.)
    project_angle = None
    is_short = out_row_dict[fld_totprojlen] <= params.tmc_buff_dist_ft * 10
    if int(arcpy.management.GetCount(fl_proj)[0]) == 1 and is_short:
        project_angle_data = compute_feature_angles(fl_proj, id_field='OBJECTID')
        project_angle = [a for a in project_angle_data.values()][0]
    
    for direcn in dirxn_list:

        # https://support.esri.com/en/technical-article/000012699
        
        # temporary files
        scratch_gdb = arcpy.env.scratchGDB
        
        temp_intersctpts = os.path.join(scratch_gdb, "temp_intersectpoints")  # r"{}\temp_intersectpoints".format(scratch_gdb)
        temp_intrsctpt_singlpt = os.path.join(scratch_gdb, "temp_intrsctpt_singlpt") # converted from multipoint to single point (1 pt per feature)
        temp_splitprojlines = os.path.join(scratch_gdb, "temp_splitprojlines") # fc of project line split up to match TMC buffer extents
        temp_splitproj_w_tmcdata = os.path.join(scratch_gdb, "temp_splitproj_w_tmcdata") # fc of split project lines with TMC data on them
        
        fl_splitprojlines = g_ESRI_variable_1
        fl_splitproj_w_tmcdata = g_ESRI_variable_2
        
        # get TMCs whose buffers intersect the project line
        arcpy.SelectLayerByLocation_management(fl_tmcs_buffd, "INTERSECT", fl_proj)
        
        # select TMC buffers that intersect the project and are in indicated direction
        sql_sel_tmcxdir = g_ESRI_variable_3.format(tmc_dir_field, direcn)
        arcpy.SelectLayerByAttribute_management(fl_tmcs_buffd, "SUBSET_SELECTION", sql_sel_tmcxdir)
        selected_tmc_cnt = int(arcpy.GetCount_management(fl_tmcs_buffd)[0])

        if project_angle and selected_tmc_cnt > 0:
            # for short, single-piece projects, find out if any TMCs it intersects should be removed because they are just cross strees
            # and thus we do not want their speed data applied for project
            tmc_subset = remove_cross_streets(fl_tmcs_buffd, tmc_lines, project_angle)
            selected_tmc_cnt = len(tmc_subset)
            if selected_tmc_cnt > 0:
                cl_no_xstreets = list2qrytuple(tmc_subset)
                qry_no_xstreets = f"{params.col_tmc_id} IN {cl_no_xstreets}"
                arcpy.management.SelectLayerByAttribute(fl_tmcs_buffd, 'SUBSET_SELECTION', qry_no_xstreets)

        # if no TMC buffers intersect project line, then set TMC length for the direction to be zero
        out_dict_len_field = f"{direcn}_calc_len"
        if selected_tmc_cnt == 0:
            out_row_dict[out_dict_len_field] = 0
        else:
            # split the project line at the boundaries of the TMC buffer, creating points where project line intersects TMC buffer boundaries
            arcpy.Intersect_analysis([fl_proj, fl_tmcs_buffd],temp_intersctpts,"","","POINT")
            arcpy.MultipartToSinglepart_management (temp_intersctpts, temp_intrsctpt_singlpt)
            
            # split project line into pieces at points where it intersects buffer, with 10ft tolerance
            # (not sure why 10ft tolerance needed but it is, zero tolerance results in some not splitting)
            arcpy.SplitLineAtPoint_management(fl_proj, temp_intrsctpt_singlpt,
                                            temp_splitprojlines, "10 Feet")
            arcpy.MakeFeatureLayer_management(temp_splitprojlines, fl_splitprojlines)
            
            # get TMC speeds onto each piece of the split project line via spatial join
            arcpy.SpatialJoin_analysis(temp_splitprojlines, fl_tmcs_buffd, temp_splitproj_w_tmcdata,
                                    "JOIN_ONE_TO_ONE", "KEEP_ALL", "#", "HAVE_THEIR_CENTER_IN", "30 Feet")
                                    
            # convert to fl and select records where "check field" col val is not none
            arcpy.MakeFeatureLayer_management(temp_splitproj_w_tmcdata, fl_splitproj_w_tmcdata)
            
            check_field = speed_data_fields[0]  # choose first speed value field for checking--if it's null, then don't include those rows in aggregation
            sql_notnull = g_ESRI_variable_4.format(check_field)
            arcpy.SelectLayerByAttribute_management(fl_splitproj_w_tmcdata, "NEW_SELECTION", sql_notnull)
            
            # convert the selected records into a numpy array then a pandas dataframe
            flds_df = [fld_shp_len] + speed_data_fields 
            df_spddata = ut.esri_object_to_df(fl_splitproj_w_tmcdata, flds_df)

            # remove project pieces with no speed data so their distance isn't included in weighting
            df_spddata = df_spddata.loc[pd.notnull(df_spddata[speed_data_fields[0]])].astype(float)
            
            # remove rows where there wasn't enough NPMRDS data to get a valid speed or reliability reading
            df_spddata = df_spddata.loc[df_spddata[flds_df].min(axis=1) > 0]
            
            dir_len = df_spddata[fld_shp_len].sum()
            out_row_dict[out_dict_len_field] = dir_len #"calc" length because it may not be same as project length
            
            
            # go through and do conflation calculation for each TMC-based data field based on correct method of aggregation
            for field, calcmthd in fields_calc_dict.items():
                if calcmthd == params.calc_inv_avg: # See PPA documentation on how to calculated "inverted speed average" method
                    sd_dict = get_wtd_speed(df_spddata, field, direcn, fld_shp_len)
                    out_row_dict.update(sd_dict)
                elif calcmthd == params.calc_distwt_avg:
                    fielddir = "{}{}".format(direcn, field)  # add direction tag to field names
                    # if there's speed data, get weighted average value.
                    linklen_w_speed_data = df_spddata[fld_shp_len].sum()
                    if linklen_w_speed_data > 0: #wgtd avg = sum(piece's data * piece's len)/(sum of all piece lengths)
                        avg_data_val = (df_spddata[field]*df_spddata[fld_shp_len]).sum() \
                                        / df_spddata[fld_shp_len].sum()
        
                        out_row_dict[fielddir] = avg_data_val
                    else:
                        out_row_dict[fielddir] = df_spddata[field].mean() #if no length, just return mean speed? Maybe instead just return 'no data avaialble'? Or -1 to keep as int?
                        continue
                else:
                    continue

    #cleanup
    fcs_to_delete = [temp_intersctpts, temp_intrsctpt_singlpt, temp_splitprojlines, temp_splitproj_w_tmcdata]
    for fc in fcs_to_delete:
        arcpy.Delete_management(fc)

    output_df = pd.DataFrame([out_row_dict])
    
    return output_df
    
    
def simplify_outputs(in_df, proj_len_col):
    dirlen_suffix = '_calc_len'
    
    proj_len = in_df[proj_len_col][0]
    
    re_lendir_col = '.*{}'.format(dirlen_suffix)
    lendir_cols = [i for i in in_df.columns if re.search(re_lendir_col, i)]
    df_lencols = in_df[lendir_cols]    
    
    max_len_col = df_lencols.idxmax(axis = 1)[0] #return column name of direction with greatest overlap
    df_lencols2 = df_lencols.drop(max_len_col, axis = 1)
    secndmax_col = df_lencols2.idxmax(axis = 1)[0] #return col name of direction with second-most overlap

    # direction names without '_calc_len' suffix
    maxdir = max_len_col[:max_len_col.find(dirlen_suffix)] 
    secdir = secndmax_col[:secndmax_col.find(dirlen_suffix)]

    outcols_max = [c for c in in_df.columns if re.match(maxdir, c)]
    outcols_sec = [f.replace(maxdir, secdir) for f in outcols_max] # this ensures that all keys are present (e.g. ff_speed) even if data aren't

    outcols = outcols_max + outcols_sec
    
    # if there's less than 10% overlap in the 'highest overlap' direction, 
    # then say that the project is not on any TMCs (and any TMC data is from cross streets or is insufficient to represent the segment)
    val_nodata = 0 # value that denotes absence of data, or project line happening where there are no data
    
    colname_dict = {max_len_col:outcols_max, secndmax_col:outcols_sec}
    for dir_col, dir_outcols in colname_dict.items():
        dir_len = in_df[dir_col][0]
        if (dir_len / proj_len) < 0.1: 
            for col in dir_outcols: in_df[col] = val_nodata

    return in_df[outcols].to_dict('records')
    
def make_df(in_dict):
    re_dirn = re.compile("(.*BOUND).*") # retrieve direction
    re_metric = re.compile(".*BOUND(.*)") # retrieve name of metric
    
    df = pd.DataFrame.from_dict(in_dict, orient=g_ESRI_variable_5)
    
    col_metric = 'metric'
    col_direction = 'direction'
    
    df[col_direction] = df.index.map(lambda x: re.match(re_dirn, x).group(1))
    df[col_metric] = df.index.map(lambda x: re.match(re_metric, x).group(1))
    
    df_out = df.pivot(index=col_metric, columns=col_direction, values=0 )
    
    return df_out


def get_npmrds_data(fc_projline, str_project_type):
    arcpy.AddMessage("Calculating congestion and reliability metrics...")
    arcpy.OverwriteOutput = True

    fl_projline = g_ESRI_variable_6
    arcpy.MakeFeatureLayer_management(fc_projline, fl_projline)

    # make feature layer from speed data feature class
    fl_speed_data = g_ESRI_variable_7
    arcpy.MakeFeatureLayer_management(params.fc_speed_data, fl_speed_data)

    # select TMCs that intersect project
    arcpy.SelectLayerByLocation_management(fl_speed_data, "WITHIN_A_DISTANCE", fl_projline, params.tmc_select_srchdist, "NEW_SELECTION")

    # further filter to only get intersecting TMCs that are not obviously cross streets
    # UPDATE NEEDED FOR THIS based on remove_cross_streets() placeholder function
    # problem is that if user draws multi-piece project and each piece is different angle, 

    # subset selection to only get TMCs that are same road type (fwy vs. arterial) as project line
    if str_project_type == params.ptype_fwy:
        sql = g_ESRI_variable_8.format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)
    else:
        sql = "{} NOT IN {}".format(params.col_roadtype, params.roadtypes_fwy)
        arcpy.SelectLayerByAttribute_management(fl_speed_data, "SUBSET_SELECTION", sql)

    # create temporary buffer layer, flat-tipped, around TMCs; will be used to split project lines
    temp_tmcbuff = os.path.join(arcpy.env.scratchGDB, "TEMP_linkbuff_4projsplit")
    fl_tmc_buff = g_ESRI_variable_9
    arcpy.Buffer_analysis(fl_speed_data, temp_tmcbuff, params.tmc_buff_dist_ft, "FULL", "FLAT")
    arcpy.MakeFeatureLayer_management(temp_tmcbuff, fl_tmc_buff)

    # buff_sr_name = arcpy.Describe(temp_tmcbuff).spatialReference.name
    # arcpy.AddMessage(f"{temp_tmcbuff} SPATIAL REF NAME: {buff_sr_name}")

    # get "full" table with data for all directions
    projdata_df = conflate_tmc2projline(fl_projline, params.directions_tmc, params.col_tmcdir,
                                        fl_tmc_buff, fl_speed_data, params.spd_data_calc_dict)

    # trim down table to only include outputs for directions that are "on the segment",
    # i.e., that have most overlap with segment
    out_dict = simplify_outputs(projdata_df, 'proj_length_ft')[0]

    #cleanup
    arcpy.Delete_management(temp_tmcbuff)

    return out_dict


# =====================RUN SCRIPT===========================
    

if __name__ == '__main__':
    from time import perf_counter as perf
    start_time = perf()

    arcpy.env.workspace = params.fgdb # r'\\data-svr\GIS\Projects\Darren\PPA3_GIS\PPA3Testing.gdb'

    project_line = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\test_avoid_cross_traff_spd' # arcpy.GetParameterAsText(0) #"NPMRDS_confl_testseg_seconn"
    proj_type = params.ptype_arterial # arcpy.GetParameterAsText(2) #"Freeway"

    #================================
    try:
        arcpy.Delete_management(arcpy.env.scratchGDB) # ensures a new, fresh scratch GDB is created to avoid any weird file-not-found errors
        print("Deleted arcpy scratch GDB to ensure reliability.")
    except:
        pass

    test_dict = get_npmrds_data(project_line, proj_type)

    print(test_dict)

    elapsed_time = round((perf() - start_time)/60, 1)
    print("Success! Time elapsed: {} minutes".format(elapsed_time))    


    


