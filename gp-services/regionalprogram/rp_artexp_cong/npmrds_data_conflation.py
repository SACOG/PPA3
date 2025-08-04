import os
import re
import math
import arcpy
import pandas as pd

from config_links import params
from utils import utils as ut


def get_weighted_speed(df, speed_field, direction, length_field):
    inv_speed_field = "spdinv_hpm"
    travel_time_field = "projpc_tt"
    length_mi_field = "pc_len_mi"

    
    df[inv_speed_field] = 1 / df[speed_field] # calculate each piece's "hours per mile", or inverted speed, as 1/speed
    
    # get each piece's travel time, in hours as inverted speed (hrs per mi) * piece distance (mi)
    df[length_mi_field] = df[length_field] / params.ft2mile
    df[travel_time_field] = df[inv_speed_field] * df[length_mi_field]

    total_distance = df[length_mi_field].sum()
    total_time = df[travel_time_field].sum()
    avg_speed = total_distance / total_time

    return {f"{direction}{speed_field}": avg_speed}


def calculate_angle(start_x, start_y, end_x, end_y):
    return math.degrees(math.atan2(end_y - start_y, end_x - start_x))


def compute_feature_angles(feature_class, id_field):
    angles = {}
    with arcpy.da.SearchCursor(feature_class, [id_field, "SHAPE@"]) as cursor:
        for row in cursor:
            start = row[1].firstPoint
            end = row[1].lastPoint
            angles[row[0]] = calculate_angle(start.X, start.Y, end.X, end.Y)
    return angles


def format_sql_in_clause(values):
    return f"('{values[0]}')" if len(values) == 1 else tuple(values)


def filter_cross_streets(buffer_layer, tmc_layer, project_angle):
    tmc_ids = [row[0] for row in arcpy.da.SearchCursor(buffer_layer, [params.col_tmc_id])]
    clause = f"{params.col_tmc_id} IN {format_sql_in_clause(tmc_ids)}"
    arcpy.management.SelectLayerByAttribute(tmc_layer, 'NEW_SELECTION', clause)

    tmc_angles = compute_feature_angles(tmc_layer, params.col_tmc_id)
    valid_tmcs = [tmc for tmc, angle in tmc_angles.items() if abs(project_angle - angle) <= 10]

    arcpy.management.SelectLayerByAttribute(tmc_layer, 'CLEAR_SELECTION')
    return valid_tmcs


def conflate_tmc_to_project(project_layer, directions, tmc_dir_field, buffer_layer, tmc_layer, field_methods):
    esri_len = "SHAPE@LENGTH"

    output = {"proj_length_ft": sum(row[0] for row in arcpy.da.SearchCursor(project_layer, [esri_len]))}
    project_angle = None

    if isinstance(params.tmc_buff_dist_ft, str): # for some reason sometimes the buffer dist may be a string, e.g. "90 Feet" instead of integer 90.
        params.tmc_buff_dist_ft = float(re.findall(r'\d+', params.tmc_buff_dist_ft)[0])

    if int(arcpy.management.GetCount(project_layer)[0]) == 1 and output["proj_length_ft"] <= params.tmc_buff_dist_ft*10:
        # if only one feature in the project, compute the angle of the project line
        # this will be used to help eliminate incorrect TMC matches for short projects
        # (e.g., a short E-W project that gets N-S congestion data wrongly tagged to it.)
        angles = compute_feature_angles(project_layer, 'OBJECTID')
        project_angle = list(angles.values())[0]

    for direction in directions:
        arcpy.SelectLayerByLocation_management(buffer_layer, "INTERSECT", project_layer)
        arcpy.SelectLayerByAttribute_management(buffer_layer, "SUBSET_SELECTION", f"{tmc_dir_field} = '{direction}'")
        selected_count = int(arcpy.GetCount_management(buffer_layer)[0])

        if project_angle and selected_count > 0:
            # for short, single-piece projects, find out if any TMCs it intersects should be removed because they are just cross strees
            # and thus we do not want their speed data applied for project
            valid_tmcs = filter_cross_streets(buffer_layer, tmc_layer, project_angle)
            selected_count = len(valid_tmcs)
            if selected_count > 0:
                clause = f"{params.col_tmc_id} IN {format_sql_in_clause(valid_tmcs)}"
                arcpy.management.SelectLayerByAttribute(buffer_layer, 'SUBSET_SELECTION', clause)

        # if no TMC buffers intersect project line, then set TMC length for the direction to be zero
        length_field = f"{direction}_calc_len"
        if selected_count == 0:
            output[length_field] = 0
            continue

        scratch = arcpy.env.scratchGDB
        inter_pts = os.path.join(scratch, "temp_intersectpoints")
        single_pts = os.path.join(scratch, "temp_intrsctpt_singlpt")
        split_lines = os.path.join(scratch, "temp_splitprojlines")
        joined_lines = os.path.join(scratch, "temp_splitproj_w_tmcdata")

        # split the project line at the boundaries of the TMC buffer, creating points where project line intersects TMC buffer boundaries
        arcpy.Intersect_analysis([project_layer, buffer_layer], inter_pts, "", "", "POINT")
        arcpy.MultipartToSinglepart_management(inter_pts, single_pts)

        # split project line into pieces at points where it intersects buffer, with 10ft tolerance
        # (zero tolerance results in some not splitting)
        arcpy.SplitLineAtPoint_management(project_layer, single_pts, split_lines, "10 Feet")

        # get TMC speeds onto each piece of the split project line via spatial join
        arcpy.SpatialJoin_analysis(split_lines, buffer_layer, joined_lines, "JOIN_ONE_TO_ONE", "KEEP_ALL", "#", "HAVE_THEIR_CENTER_IN", "30 Feet")

        # convert to fl and select records where "check field" col val is not none
        fl_joinedlines = "fl_joinedlines"
        arcpy.MakeFeatureLayer_management(joined_lines, fl_joinedlines)
        
        # choose first speed value field for checking--if it's null, then don't include those rows in aggregation
        check_field = list(field_methods.keys())[0]
        arcpy.SelectLayerByAttribute_management(fl_joinedlines, "NEW_SELECTION", f"{check_field} IS NOT NULL")

        # .dropna() to remove project pieces with no speed data so their distance isn't included in weighting
        fields = [esri_len] + list(field_methods.keys())
        df = ut.esri_object_to_df(fl_joinedlines, fields).dropna().astype(float)

        # remove rows where there wasn't enough NPMRDS data to get a valid speed or reliability reading
        df = df[df[fields].min(axis=1) > 0]

        output[length_field] = df[esri_len].sum() #calc'd direction length because it may not be same as project length

        # go through and do conflation calculation for each TMC-based data field based on correct method of aggregation
        for field, method in field_methods.items():
            if method == params.calc_inv_avg: # See PPA documentation on how to calculated "inverted speed average" method
                output.update(get_weighted_speed(df, field, direction, esri_len))
            elif method == params.calc_distwt_avg:
                result = df[field].mean() # default is to compute simple unweighted avg.
                if df[esri_len].sum() > 0: # but normally compute distance-wtd avg
                    result = (df[field] * df[esri_len]).sum() / df[esri_len].sum()
                output[f"{direction}{field}"] = result

        for fc in [inter_pts, single_pts, split_lines, joined_lines]:
            arcpy.Delete_management(fc)

    return pd.DataFrame([output])


def simplify_output(df, length_col):
    suffix = '_calc_len'
    total_length = df[length_col][0]
    length_cols = [col for col in df.columns if col.endswith(suffix)]

    # return field names for directions with most and second-most overlap
    max_col = df[length_cols].idxmax(axis=1)[0] 
    second_col = df[[col for col in length_cols if col != max_col]].idxmax(axis=1)[0] 

    max_dir = max_col.replace(suffix, '')
    sec_dir = second_col.replace(suffix, '')

    # strip '_calc_len' suffix from direction field names
    max_fields = [col for col in df.columns if col.startswith(max_dir)]
    sec_fields = [col.replace(max_dir, sec_dir) for col in max_fields] # this ensures that all keys are present (e.g. ff_speed) even if data aren't

    for col_set, col_name in zip([max_fields, sec_fields], [max_col, second_col]):
        if df[col_name][0] / total_length < 0.1:
            for col in col_set:
                df[col] = 0

    return df[max_fields + sec_fields].to_dict('records')


def get_npmrds_data(project_fc, project_type):
    arcpy.env.overwriteOutput = True
    arcpy.AddMessage("Calculating congestion and reliability metrics...")

    fl_proj = "fl_project"
    arcpy.MakeFeatureLayer_management(project_fc, fl_proj)

    fl_speed = "fl_speed_data"
    arcpy.MakeFeatureLayer_management(params.fc_speed_data, fl_speed)

    arcpy.SelectLayerByLocation_management(fl_speed, "WITHIN_A_DISTANCE", fl_proj, params.tmc_select_srchdist)

    if project_type in params.ptypes_fwy:
        sql = f"{params.col_roadtype} IN {params.roadtypes_fwy}"
    else:
        sql = f"{params.col_roadtype} NOT IN {params.roadtypes_fwy}"
    arcpy.SelectLayerByAttribute_management(fl_speed, "SUBSET_SELECTION", sql)

    buffer_fc = os.path.join(arcpy.env.scratchGDB, "TEMP_linkbuff_4projsplit")
    arcpy.Buffer_analysis(fl_speed, buffer_fc, params.tmc_buff_dist_ft, "FULL", "FLAT")
    arcpy.MakeFeatureLayer_management(buffer_fc, "fl_tmc_buff")

    df = conflate_tmc_to_project(fl_proj, params.directions_tmc, params.col_tmcdir, "fl_tmc_buff", fl_speed, params.spd_data_calc_dict)
    result = simplify_output(df, 'proj_length_ft')[0]

    arcpy.Delete_management(buffer_fc)
    return result


if __name__ == '__main__':
    from time import perf_counter
    start = perf_counter()

    arcpy.env.workspace = params.fgdb
    project_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3Testing.gdb\Test_I5_NoNa'
    project_type = params.ptype_arterial

    try:
        arcpy.Delete_management(arcpy.env.scratchGDB)
        print("Deleted arcpy scratch GDB to ensure reliability.")
    except Exception:
        pass

    result = get_npmrds_data(project_fc, project_type)
    print(result)

    elapsed = round((perf_counter() - start) / 60, 1)
    print(f"Success! Time elapsed: {elapsed} minutes")

