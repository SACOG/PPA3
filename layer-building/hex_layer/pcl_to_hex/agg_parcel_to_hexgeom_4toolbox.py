# -*- coding: utf-8 -*-
#--------------------------------
# Name:agg_parcel_to_hexgeom.py
# Purpose: intersect parcel and hexagon polygon files to allow area-weighted
#          aggregations of parcel data onto hex polygons
#           
# Author: Darren Conly
# Last Updated: Feb 2025
# Updated by: <name>
# Copyright:   (c) SACOG
# Python Version: 3.x
#--------------------------------
from pathlib import Path
import os
import time
import datetime as dt
import arcpy

arcpy.env.overwriteOutput = True

#==============================

#divide parcel polygons at hex boundaries
def do_intersect(fc_parcels, fc_hexs, fc_intersect_base, fld_pcltotarea): #clean up, fc_intersect doesn't need to be argument; is temp layer
    
    #add field with parcel's total area
    arcpy.AddMessage("Intersecting {} with {}...".format(fc_parcels, fc_hexs))
    if fld_pcltotarea not in [f.name for f in arcpy.ListFields(fc_parcels)]:
        arcpy.AddField_management(fc_parcels, fld_pcltotarea, "FLOAT")
    
    area_pcl = "SHAPE@AREA"
    fields = [fld_pcltotarea, area_pcl]
    
    
    with arcpy.da.UpdateCursor(fc_parcels, fields) as cur:
        for row in cur:
            row[fields.index(fld_pcltotarea)] = row[fields.index(area_pcl)]
            cur.updateRow(row)
    
    #do intersection
    in_features = [fc_parcels, fc_hexs]
    arcpy.Intersect_analysis(in_features, fc_intersect_base)
    
#join ILUT data to polygons formed by intersecting parcel polys with hexes
# join_ilut_to_intersect(pcl_intersect_layer, tbl_ilutdata, ilut_val_fields, tempfc_intsct_w_ilut, fld_pcl_id)
def join_ilut_to_intersect(fc_intersect_base, tbl_ilutdata, ilut_fields, tempfc_intsct_w_ilut, fld_pcl_id):
    arcpy.AddMessage("Joining {} ILUT data to hex-parcel intersect layer...\n".format(tbl_ilutdata))

    arcpy.Copy_management(fc_intersect_base, tempfc_intsct_w_ilut)
    
    arcpy.env.qualifiedFieldNames = False
    
    
    #join ILUT or other parcel-level data to parcel pieces in intersect layer
    fl_ix_fields = [f.name for f in arcpy.ListFields(tempfc_intsct_w_ilut)]
    ilut_field_info = {f.name: f.type for f in arcpy.ListFields(tbl_ilutdata) if f.name in ilut_fields}

    dtype_conversion = {'Single': 'DOUBLE', 'Integer': 'LONG',
                        'Double': 'DOUBLE', 'SmallInteger': 'SHORT',
                        'String': 'TEXT'}
    for fname, ftype in ilut_field_info.items():
        if fname not in fl_ix_fields:
            arcpy.management.AddField(tempfc_intsct_w_ilut, fname, dtype_conversion[ftype])
    
    ilut_fields_ordered = list(ilut_field_info.keys())
    data_rows = {}
    cur_fields = [fld_pcl_id, *ilut_fields_ordered]
    with arcpy.da.SearchCursor(tbl_ilutdata, cur_fields) as scur:
        for row in scur:
            id_idx = cur_fields.index(fld_pcl_id)
            pid = row[id_idx]
            row_data = [i for i in row if i != pid]
            data_rows[pid] = row_data

    with arcpy.da.UpdateCursor(tempfc_intsct_w_ilut, cur_fields) as ucur:
        for row in ucur:
            pid = row[cur_fields.index(fld_pcl_id)]
            new_data = data_rows.get(pid) 
            if not new_data:
                new_data = [0 for i in ilut_fields_ordered]

            new_row = [pid, *new_data]
            ucur.updateRow(new_row)

    
def calc_propl_val(fc_intersect_w_propn, fld_pcltotarea, fldin, fldoutprefix, agg_type, sufx_proplflds):
    
    #add field which'll be populated with the % of parcel that's in hex, as well as weighted value
    fld_pclareapct = "pctpclarea"
    fld_wtd_val = "{}{}".format(fldoutprefix, sufx_proplflds) #get area weighted value for each parcel piece (value = pop, emp, whatever)
    
    if fld_pclareapct not in [f.name for f in arcpy.ListFields(fc_intersect_w_propn)]:
        arcpy.AddField_management(fc_intersect_w_propn, fld_pclareapct, "FLOAT")
    
    if fld_wtd_val not in [f.name for f in arcpy.ListFields(fc_intersect_w_propn)]:
        arcpy.AddField_management(fc_intersect_w_propn, fld_wtd_val, "FLOAT")
    
    fl_intersectjoin = "fl_intersectjoin"
    arcpy.MakeFeatureLayer_management(fc_intersect_w_propn, fl_intersectjoin)
    
    fields = [f.name for f in arcpy.ListFields(fl_intersectjoin)]
    fields.append("SHAPE@AREA")
    
    with arcpy.da.UpdateCursor(fl_intersectjoin, fields) as cur:
        for row in cur:
            # compute values for parcel pieces. Depending on aggregation method (mean or sum),
            # pieces' values will be pro-rated by area, or left unchanged from whole-parcel value.
            
            pcl_val = row[fields.index(fldin)]
            if pcl_val is None:
                share_val = 0
            else:
                if isinstance(pcl_val, str):
                    pcl_val = float(pcl_val)
    
                if agg_type == 'SUM': # if ultimately *summing* by hex, get area-proportional value (of pop, emp, etc) for each polygon piece
                    area_piece = row[fields.index("SHAPE@AREA")]
                    area_totalpcl = row[fields.index(fld_pcltotarea)]
                    pclshare = area_piece / area_totalpcl
                    row[fields.index(fld_pclareapct)] = pclshare
                    share_val = pcl_val * pclshare #e.g. if piece's area is half of parcel's and we want pop, then (pop for entire parcel) * 0.5
                elif agg_type == 'MEAN': # but if getting average (e.g., average mix-index value), the mix index is same for parcel pieces as it is for entire parcel
                    share_val = pcl_val
                else:
                    raise Exception(f"agg_type {agg_type} not valid. Must be 'SUM' or 'MEAN'.")
            row[fields.index(fld_wtd_val)] = share_val
            
            cur.updateRow(row)


#dissolve by hex ID; getting sum, avg, etc. of the values weighted by parcel piece area
def dissolve_x_hex(fc_intersect_w_propn, dict_fld_pcl_vals, sufx_proplflds, fc_hexs, fld_hexid, fc_hexoutput):

    def agg_wtd_avg(ix_val_field, skip_vals=None):
        # gets avg value of ix_val field within hexid weighted by intersection "piece" area
        result_dict = {}
        f_ix_area = 'SHAPE@AREA'
        ix_fields = [fld_hexid, ix_val_field, f_ix_area]
        with arcpy.da.SearchCursor(fc_intersect_w_propn, ix_fields) as scur:
            for row in scur:
                val = row[ix_fields.index(ix_val_field)]
                if skip_vals and val in skip_vals:
                    continue # do not include values that represent null/excluded values

                area = row[ix_fields.index(f_ix_area)]
                hexid = row[ix_fields.index(fld_hexid)]
                if result_dict.get(hexid) is None:
                    result_dict[hexid] = {'spval': 0, 'area': 0}
                    result_dict[hexid]['spval'] = val*area
                    result_dict[hexid]['area'] = area
                else:
                    result_dict[hexid]['spval'] += val*area
                    result_dict[hexid]['area'] += area
        
        result_dict = {hexid: hexvals['spval'] / hexvals['area'] for hexid, hexvals in result_dict.items()}

        return result_dict

    def agg_sum(ix_val_field):
        # gets avg value of ix_val field within hexid weighted by intersection "piece" area

        result_dict = {}
        ix_fields = [fld_hexid, ix_val_field]
        with arcpy.da.SearchCursor(fc_intersect_w_propn, ix_fields) as scur:
            for row in scur:
                val = row[ix_fields.index(ix_val_field)]
                hexid = row[ix_fields.index(fld_hexid)]
                if result_dict.get(hexid) is None:
                    result_dict[hexid] = val
                else:
                    result_dict[hexid] += val

        return result_dict
        
    def agg_to_hex(ix_val_field, aggfunc_name='SUM'):

        aggfunc_spec = {'MEAN': [agg_wtd_avg, (ix_val_field, -1)],
                        'SUM': [agg_sum, (f"{ix_val_field}{sufx_proplflds}",)]} # need trailing comma to have *starring split correctly
        
        aggfunc = aggfunc_spec[aggfunc_name][0]
        agg_args = aggfunc_spec[aggfunc_name][1]
        try:
            result_dict = aggfunc(*agg_args)
        except:
            import pdb; pdb.set_trace()

        if ix_val_field not in [f.name for f in arcpy.ListFields(fc_hexoutput)]:
            arcpy.management.AddField(fc_hexoutput, ix_val_field, 'DOUBLE')

        upd_fields = [fld_hexid, ix_val_field]
        with arcpy.da.UpdateCursor(fc_hexoutput, upd_fields) as ucur:
            for row in ucur:
                hexid = row[upd_fields.index(fld_hexid)]
                hexval = result_dict.get(hexid)
                if hexval:
                    row[upd_fields.index(ix_val_field)] = hexval
                else:
                    row[upd_fields.index(ix_val_field)] = 0 # if no value in hex base, then assume zero
                ucur.updateRow(row)


    arcpy.AddMessage("aggregating to hex geometry...\n")
    
    arcpy.env.qualifiedFieldNames = False #ensures original table names do not append to joined fields after exporting joined layers.

    arcpy.Copy_management(fc_hexs, fc_hexoutput)
    
    #summarize by hex ID, outputting table
    # dict with agg spec for each field - {field name: agg method}
    for fname, aggfunc in dict_fld_pcl_vals.items():
        print(f"computing {aggfunc} of {fname} within each hexagon...")
        agg_to_hex(fname, aggfunc_name=aggfunc)
    
    arcpy.Delete_management(fc_intersect_w_propn)
    

def do_work(fc_parcels, fc_hexs, fld_hexid, tbl_ilutdata, fld_pcl_id, dict_fld_pcl_vals, pcl_intersect_layer=None):
    
    time_id = str(dt.datetime.now().strftime('%Y%m%d%H%M'))
    fld_pcltotarea = "pcltotarea" #clean this up. This variable is declared twice

    ilut_tblname = os.path.basename(tbl_ilutdata).split('ilut_combined')[1]
    fc_hexoutput = f"hex_ILUT{ilut_tblname}{time_id}"
    
    #make layer that's intersect of parcels and hexs
    if pcl_intersect_layer is None or pcl_intersect_layer == '':
        print('\nMaking new parcel-hex intersecting layer...')
        pcl_intersect_layer = "PclHexIntersect_base"
        do_intersect(fc_parcels, fc_hexs, pcl_intersect_layer, fld_pcltotarea)
    
    #join ILUT data to the intersect layer
    tempfc_intsct_w_ilut = str(Path(arcpy.env.scratchGDB).joinpath(f"TEMPintsct_w_ILUT{time_id}"))
    ilut_val_fields = list(dict_fld_pcl_vals.keys())
    join_ilut_to_intersect(pcl_intersect_layer, tbl_ilutdata, ilut_val_fields, tempfc_intsct_w_ilut, fld_pcl_id)
    
    sufx_proplflds = "_propl" #suffix to give to field names to indicate they're proportional to share of parcel
    
    #calculate area-weighted ILUT values for hexes
    fc_intsct_out = f"PclHexIntsct_wValPropns{time_id}"
    arcpy.CopyFeatures_management(tempfc_intsct_w_ilut, fc_intsct_out)
    
    for fname, aggtype in dict_fld_pcl_vals.items():
        arcpy.AddMessage(f"calculating {fname} proportional values...\n")
        calc_propl_val(fc_intsct_out, fld_pcltotarea, fname, fname, aggtype, sufx_proplflds)
    
    dissolve_x_hex(fc_intsct_out, dict_fld_pcl_vals, sufx_proplflds, fc_hexs, fld_hexid, fc_hexoutput)
    arcpy.Delete_management(tempfc_intsct_w_ilut)

    return fc_hexoutput
        

if __name__ == '__main__':
    start_time = time.time()
    date_sufx = str(dt.date.today().strftime('%Y%m%d'))
    
    #user input parameters
    arcpy.env.workspace = arcpy.GetParameterAsText(0)
    fc_parcels = arcpy.GetParameterAsText(1)
    fc_hexs = arcpy.GetParameterAsText(2)
    tbl_ilutdata = arcpy.GetParameterAsText(3)   # data table that contains population, emp, other data you want to summarize at hex level
    flds_ilut_to_calc = arcpy.GetParameterAsText(4) #NEXT STEP - enable user to specify type of statistic th ey want calc'd for each field (e.g. sum, avg, etc.)
    pcl_intersect_layer = arcpy.GetParameterAsText(5) #if intersected hex-parcel layer already done, using it will save ~3mins of run time by skipping its creation and using existing one

    # hard-coded vals for testing
    # arcpy.env.workspace = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb'
    # fc_parcels = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\parcel_data_poly_2020'
    # fc_hexs = r'I:\SDE_Connections\SDE-PPA\owner@PPA.sde\OWNER.RegionHex'
    # tbl_ilutdata = r'I:\Projects\Darren\PPA3_GIS\winuser@MTP2024.sde\dbo.ilut_combined2020_63_DPS'   # data table that contains population, emp, other data you want to summarize at hex level
    # flds_ilut_to_calc = 'POP_TOT SUM' # 'POP_TOT SUM;MIXINDEX MEAN'
    # pcl_intersect_layer = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\PclHexIntersect_base' #if intersected hex-parcel layer already done, using it will save ~3mins of run time by skipping its creation and using existing one


    #==================================
    fld_pcl_id = 'parcelid' #join field for parcelid--should be same for all tables
    fld_hexid = "GRID_ID"

    if arcpy.Exists(arcpy.env.scratchGDB):
        arcpy.Delete_management(arcpy.env.scratchGDB)

    field_agg_spec = {} # {field name: agg method}
    for finfo in flds_ilut_to_calc.split(';'):
            info_split = finfo.split(' ')
            spec_entry = {info_split[0]: info_split[1]}
            field_agg_spec.update(spec_entry) 

    arcpy.AddMessage(field_agg_spec)
    
    result_hexes = do_work(fc_parcels, fc_hexs, fld_hexid, tbl_ilutdata, fld_pcl_id, field_agg_spec, pcl_intersect_layer)
    
    elapsed_time = round((time.time() - start_time)/60,1)
    arcpy.AddMessage("Success! Elapsed time: {} minutes".format(elapsed_time))
    arcpy.AddMessage("Output file: {}".format(os.path.join(arcpy.env.workspace, result_hexes)))
    
    
