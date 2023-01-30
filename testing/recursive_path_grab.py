"""
Name: recursive_path_grab.py
Purpose: Search through subfolders and grab specific file


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x

"""
from pathlib import Path

in_folder = r'D:\PPA Folders to Scan\MaintMod\Applications'

ppa_rpt_fname = 'PPA Report.pdf'

path = Path(in_folder)

jur_folders = [i for i in path.iterdir()]

paths = {}

for folder in jur_folders:
    paths[folder.name] = ''
    for po in folder.rglob("*"):
        if po.name == ppa_rpt_fname:
            paths[folder.name] = (str(po))

for k, v in paths.items():
    print(f"{k}: {v}")



# if __name__ == '__main__':
#     pass