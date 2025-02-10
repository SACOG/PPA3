"""
Name: ppa_model_links.py
Purpose: 


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path

import arcpy
import pandas as pd
from dbfread import DBF

from netpyconvert import netpyconvert as npc

def dbf2df(dbf_path, fields_to_load):
	# maybe faster, and more memory-efficient, way to load big DBF into pandas dataframe
	dbf_obj = DBF(dbf_path)

	data_rows = []
	for row in dbf_obj:
		row2append = {}
		for fname, fval in row.items():
			if fname in fields_to_load: row2append[fname] = fval
		data_rows.append(row2append)
	
	df_out = pd.DataFrame(data_rows)

	return df_out

def get_model_link_data(run_folder, scen_year, daynet_net, result_gdb):

    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2226)
    arcpy.env.overwriteOutput = True
    if arcpy.Exists(arcpy.env.scratchFolder):
        arcpy.Delete_management(arcpy.env.scratchFolder)

    f_nodea = 'A'
    f_nodeb = 'B'

    # convert daynet to SHP then export to GIS database as feature class
    temp_shp = str(Path(arcpy.env.scratchFolder).joinpath("TEMP_model_links.shp"))
    temp_shp = npc.net2linkshp(in_net_path=daynet_net, scenario_prefix=scen_year, out_link_path=temp_shp)
    
    out_fc = str(Path(result_gdb).joinpath(f"model_links_{scen_year}"))
    sql_real_roads = "CAPCLASS < 62" # exclude non-real links like centroid connectors, disabled links, etc.
    arcpy.ExportFeatures_conversion(temp_shp, out_fc, where_clause=sql_real_roads)

    # get transit vol data on each link
    f_trnvol = 'TOT_TRNVOL'
    print("adding transit volume data to model links...")
    trndata_dbf = Path(run_folder).joinpath(f"trans.link.all.dbf")
    trn_cols = [f_nodea, f_nodeb, 'VOL', 'REV_VOL']
    df_trndata = dbf2df(dbf_path=trndata_dbf, fields_to_load=trn_cols)
    df_summed = df_trndata.groupby([f_nodea, f_nodeb]).sum().reset_index()
    df_summed[f_trnvol] = df_summed['VOL'] + df_summed['REV_VOL']
    df_summed['LINKID'] = df_summed[f_nodea].astype('str') + '_' + df_summed[f_nodeb].astype('str')
    del df_summed['VOL'], df_summed['REV_VOL'], df_summed[f_nodea], df_summed[f_nodeb]

    trn_data = {i['LINKID']: i['TOT_TRNVOL'] for i in df_summed.to_dict('records')}

    # add field for trn vol to model links
    print("adding transit data field...")
    if f_trnvol in [f.name for f in arcpy.ListFields(out_fc)]:
        arcpy.DeleteField_management(out_fc, f_trnvol)

    arcpy.AddField_management(out_fc, f_trnvol, 'DOUBLE')

    # join transit vol data to link data
    print("adding transit data...")
    try:
        with arcpy.da.UpdateCursor(out_fc, field_names=[f_nodea, f_nodeb, f_trnvol]) as ucur:
            for row in ucur:
                linkid = f"{row[0]}_{row[1]}"
                tvol = trn_data.get(linkid)
                if not tvol: tvol = 0 # if link not found in transit file, assume it has no transit service on it.
                row[2] = tvol
                ucur.updateRow(row)
    except:
        import pdb; pdb.set_trace()

    return out_fc
                


if __name__ == '__main__':
    daynet = input('Enter path to PPA daynet file (run daynet_ppa.s to create if needed): ').strip("\"") # r"\\win11-model-1\d$\SACSIM23\2035\DPS\run_2035_176_SOV70_Tele23_newNets\run_folder\2035daynet_ppa.net"
    sc_year = int(input('Enter scenario year: '))
    result_fgdb = input('Enter path to output file geodatabase: ').strip("\"")
    run_dir = str(Path(daynet).parent)

    result = get_model_link_data(run_dir, sc_year, daynet, result_fgdb)
    print(result)