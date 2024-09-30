"""
Name: bulk_file_compare.py
Purpose: compares 1 file to many potential candidate duplicates.
    useful, for example, to see if utils.py is same for all GP services.


Author: Darren Conly
Last Updated: Oct 2024
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path
import difflib


f1 = r'C:\Users\dconly\GitRepos\PPA3\gp-services\regionalprogram\rp_artexp_cong\utils\utils.py'
f2 = r'C:\Users\dconly\GitRepos\PPA3\gp-services\regionalprogram\rp_artexp_econ\utils\utils.py'

with open(f1) as file_1: 
    file_1_text = file_1.readlines() 
  
with open(f2) as file_2: 
    file_2_text = file_2.readlines() 
  
# Find and print the diff: 
for line in difflib.unified_diff( 
        file_1_text, file_2_text, fromfile=f1,  
        tofile=f2, lineterm='\n'): 
    print(line) 




# if __name__ == '__main__':
    