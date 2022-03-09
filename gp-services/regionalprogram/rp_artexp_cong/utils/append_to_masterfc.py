"""
Name: append_to_masterfc.py
Purpose: Take a project line from a PPA tool run and append it to a master feature class
    containing all lines from all project runs.


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import arcpy
import utils as ut
import parameters as params

def append_proj_to_master_fc(project_fc, proj_attributes_dict, master_fc):
    '''Takes project line and appends it to master line feature class with all lines users have entered'''
    arcpy.AddMessage("Archiving project line geometry...")
    #get geometry of user-drawn input line
    try:
        fld_shape = "SHAPE@"
        geoms = []
        with arcpy.da.SearchCursor(project_fc, fld_shape) as cur:
            for row in cur:
                geoms.append(row[0])
        
        #make row that will be inserted into master fc
        new_row = geoms + [v for k, v in proj_attributes_dict.items()]
        
        # use insert cursor to add in appropriate project name, etc.
        fields = [fld_shape] + list(proj_attributes_dict.keys())
        
        inscur = arcpy.da.InsertCursor(master_fc, fields)
        inscur.insertRow(new_row)
        
        del inscur
        
        t_returns = (params.msg_ok,)
    except:
        msg = ut.utils.trace()
        t_returns = (msg,)
    
    return t_returns



if __name__ == '__main__':
    pass