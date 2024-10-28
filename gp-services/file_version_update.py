"""
Name: file_version_update.py
Purpose: Take one file and update all versions in other GP services by copying it


Author: Darren Conly
Last Updated: Apr 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path
import shutil


#=========INPUT PARAMETERS============
"""
BE CAREFUL RUNNING THIS SCRIPT--IT MASS-UPDATES POTENTIALLY MANY FILES.
"""

# file you want to copy to multiple other folders
file_to_copy = Path(r"C:\Users\dconly\GitRepos\PPA3\gp-services\regionalprogram\rp_title_guidepg\commtype.py")

dest_root_dir = Path(r'C:\Users\dconly\GitRepos\PPA3\gp-services\regionalprogram')
subfolder = '' # r'utils' # folder within each GP service's folder, if not using, set value to empty string ('')

# among folders listed, specify which folders you want to update, based on first letters in file name
# is case-sensitive
prefix = 'rp' # 'cdp' 

#============RUN SCRIPT===============
# name of file you want to replace--should normally be same name as the file you're copying
file_name_to_replace = file_to_copy.name

root_dirs = [i for i in dest_root_dir.glob(f'{prefix}*') if i.is_dir()]


for rdir in root_dirs:
    dest_dir = rdir.joinpath(subfolder)
    dest_file = dest_dir.joinpath(file_name_to_replace)

    # don't copy over if destination is same as origin, or if the destination directory doesn't 
    if dest_file == file_to_copy or dest_file.exists() is False:
        print(f"skipping for {rdir}")
        continue
    else:
        shutil.copyfile(file_to_copy, dest_file)
        print(f"Replaced {dest_file}")








    
