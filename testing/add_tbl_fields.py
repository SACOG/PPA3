from dataclasses import fields
import arcpy


if __name__ == '__main__':
    arcpy.env.workspace = r'\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb'
    tbl = 'rp_fwy_cong'

    fields_to_add = ['congspd_wrst', 'congrat_wrst', 'lottr_ampk_wrst', 'lottr_midday_wrst', 'lottr_pmpk_wrst', 'lottr_wknd_wrst']

    for f in fields_to_add:
        arcpy.AddField_management(tbl, field_name=f, field_type='FLOAT')