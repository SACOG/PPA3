"""
Name: fgdb.py
Purpose: defines elements and parameters relevant to searching
    PPA output file geodatabase for matches in performance outcomes for specified report


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""


class reportDatabase:
    def __init__(self, fgdb_path):

        self.fgdb_path = fgdb_path

        self.subrpt_dict = {
            "Freeway Expansion": {
                "Reduce VMT": "rp_fwy_vmt"
            }
        }



if __name__ == '__main__':
    pass