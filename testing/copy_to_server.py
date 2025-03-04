"""
Name: copy_to_server.py
Purpose: 


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path
import shutil

def print_file_paths(src_root, srctag, dst_root, dsttag, file_name):
    def get_files(root_folder, pgmtag, filename):
        paths = []
        gps = sorted([f for f in Path(root_folder).glob(f'{pgmtag}*') if f.is_dir()])
        for gpfolder in gps:
            for f in gpfolder.rglob(f'{filename}*'):
                if f.is_file(): paths.append(f)

        return paths

    sources = get_files(src_root, srctag, file_name)
    dests = get_files(dst_root, dsttag, file_name)

    for s in sources: print(s)

    print('---')
    for d in dests: print(d)

def move_files(lkp_tbl, src_col, dest_col):
    # ISSUE - RUNS INTO PERMISSIONS ERROR
    import pandas as pd
    lkp = pd.read_csv(lkp_tbl).to_dict(orient='records')
    for row in lkp:
        import pdb; pdb.set_trace()
        shutil.copy(src=row[src_col], dst=row[dest_col])
        print(f"copied {row[src_col]} to {row[dest_col]}")

if __name__ == '__main__':
    scriptname = 'utils.py'
    src_rootdir = r'\\win10-model-2\Users\dconly\GitRepos\PPA3\gp-services\regionalprogram'
    stag = 'rp'

    dst_rootdir = r'C:\arcgisserver\directories\arcgissystem\arcgisinput'
    dtag = 'RP'

    in_csv = r"\\win10-model-2\Users\dconly\GitRepos\PPA3\testing\utils_copy_lookup.csv"
    scol = 'SOURCE'
    dcol = 'DEST'

    move_files(in_csv, scol, dcol)

##    print_file_paths(src_root=src_rootdir, srctag=stag, 
##                      dst_root=dst_rootdir, dsttag=dtag, file_name=scriptname)
