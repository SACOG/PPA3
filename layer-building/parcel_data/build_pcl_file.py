"""
Name: build_pcl_file.py
Purpose: Create PPA land use parcel file


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

def make_ppa_pcl_pts():
    # export sql query to feature class with ILUT fields (will build geom from x/y coords)
    # query must pull in LU from ETO; rename to LUTYPE in query
    # export to scratch GDB; okay to overwrite

    # create point fc from table based on table's x/y coords; will have ILUT data; make in output FGDB

    #




if __name__ == '__main__':
    pass