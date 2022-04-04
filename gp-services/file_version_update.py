"""
Name: file_version_update.py
Purpose: Take one file and update all versions in other GP services by copying it


Author: Darren Conly
Last Updated: Apr 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from logging import root
import shutil
import os
import re


#=========INPUT PARAMETERS============
"""
BE CAREFUL RUNNING THIS SCRIPT--IT MASS-UPDATES POTENTIALLY MANY FILES.
"""

# file you want to copy to multiple other folders
file_to_copy = r"C:\Users\Admin\Desktop\PPA_related\make_map_img.py"

# name of file you want to replace--should normally be same name as the file you're copying
file_name_to_replace = "make_map_img.py"

dest_root_dir = r'C:\arcgisserver\directories\arcgissystem\arcgisinput'
subfolder = r'extracted\p20\regionalprogram\utils' # folder within each folder, if needed

# among folders listed, specify which folders you want to update, based on first letters in file name
# is case-sensitive
prefix = 'RP' 

#============RUN SCRIPT===============
root_items = os.listdir(dest_root_dir)
root_dirs = [i for i in root_items if not os.path.isfile(os.path.join(dest_root_dir, i))] # list out all folders in root dir

for rdir in root_dirs:
    if re.match(f"^{prefix}", rdir):
        dest_file = os.path.join(dest_root_dir, rdir, subfolder, file_name_to_replace)
        if dest_file == file_to_copy:
            continue
        shutil.copyfile(file_to_copy, dest_file)
        print(f"Replaced {dest_file}")








    
