"""
Name: netpyconvert.py
Purpose: Functions you can call in a python script that convert a Cube NET file
    to common GIS or table files like node dbf, link shp, etc.


Author: Darren Conly
Last Updated: 
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path
import subprocess
import datetime as dt

def remove_last_prn(run_folder):
    # removes most recent-created PRN file; helps prevent lots of junk PRN files cluttering up run folders.
    fp = Path(run_folder)
    prns = {f.stat().st_ctime: f  for f in fp.glob('*.PRN')} # list of all PRNs in folder
    last_ctime = max(prns.keys()) # time of last created PRN
    last_prn = prns[last_ctime]
    
    # get minutes elapsed since last PRN was created--only want to delete if very recently created
    elapsed = dt.datetime.now() - dt.datetime.fromtimestamp(last_ctime) 
    elapsed_mins = elapsed.days*1440 + elapsed.seconds/60
    
    still_delete = True
    if elapsed_mins > 3:
        input_msg = f"""{last_prn} created {round(elapsed_mins)} mins ago and may not be from this script.
            Still delete it (leave blank if NO)?"""
        still_delete = bool(input(input_msg))
    
    if still_delete: last_prn.unlink()

def run_voyager_from_template(net_fpath, in_template_script, out_file_path, scenario_pref):
    formatted_script = net_fpath.with_stem(f"net2dbf").with_suffix(f'.s') # make copy of script with tokens filled, in model run folder

    with open(in_template_script, 'r') as f:
        str_script = f.read()

    # replace token values with correct values for input/output file
    params_list = dict(input_net=str(net_fpath), output_path=str(out_file_path))
    str_script_formatted = str_script.format(**params_list)

    # export to script in model run folder that has correct token values filled in
    with open(formatted_script, 'w') as f2:
        f2.write(str_script_formatted)

    # run the filled-in script, outputting resulting file into model run folder
    # NOTE, for some reason it won't create the DBF if run in silent mode (adding arg "/s")
    subprocess.run(['Voyager.exe', str(formatted_script), f'-P{scenario_pref}', '/Start', '/Hide'], shell=True)

# convert NET to node DBF
def net2nodedbf(in_net_path, scenario_prefix, out_dbf=None, skip_if_exists=False):
    # takes template voyager script, fills in file path args, then outputs DBF of nodes from a Cube NET file (in_net_path)
    net_file_path = Path(in_net_path)
    voyager_script_template = Path(__file__).parent.joinpath('net2nodedbf_template.s')
    
    if out_dbf is None:
        out_dbf = net_file_path.with_stem(f"{net_file_path.stem}NODES").with_suffix(f'.dbf') # fpath of output node DBF, if not provided by user
    
    out_dbf = Path(out_dbf)

    if skip_if_exists and out_dbf.exists():
        print(f"Node DBF {str(out_dbf)} already exists, so skipping its creation")
        pass

    else:
        print(f"Converting NET file {net_file_path.name} to link SHP {out_dbf.name}...")

        run_voyager_from_template(net_fpath=net_file_path, in_template_script=voyager_script_template,
                                out_file_path=out_dbf, scenario_pref=scenario_prefix)
        
        remove_last_prn(str(net_file_path.parent))

   
    return str(out_dbf)


# Convert NET to link SHP
def net2linkshp(in_net_path, scenario_prefix, out_link_path=None, skip_if_exists=False):
    # takes template voyager script, fills in file path args, then outputs DBF of nodes from a Cube NET file (in_net_path)
    net_file_path = Path(in_net_path)
    voyager_script_template = Path(__file__).parent.joinpath('net2linkshp_template.s')
    
    if out_link_path is None:
        outshp_stem = f"{net_file_path.stem}LINKS"
        out_link_dir = net_file_path.parent.joinpath(outshp_stem)
        out_link_dir.mkdir(parents=True, exist_ok=True)

        out_link_path = out_link_dir.joinpath(outshp_stem).with_suffix(f'.shp') # fpath of output node DBF, if not provided by user
    
    out_link_path = Path(out_link_path)

    if skip_if_exists and out_link_path.exists():
        print(f"Link SHP {str(out_link_path)} already exists, so skipping its creation")
        pass

    else:
        print(f"Converting NET file {net_file_path.name} to link SHP {out_link_path.name}...")

        run_voyager_from_template(net_fpath=net_file_path, in_template_script=voyager_script_template,
                                out_file_path=out_link_path, scenario_pref=scenario_prefix)
        
        remove_last_prn(str(net_file_path.parent))

    return str(out_link_path)


if __name__ == '__main__':

    net_file = r'D:\SACSIM23\faresystem_change\SACSIM23.01.03_2016_baseline_2\2016_base.net'
    sc_token = 2016

    dbf_out = net2nodedbf(in_net_path=net_file, scenario_prefix=sc_token, out_dbf=None)
    print(dbf_out)

    # net2linkshp(in_net_path=net_file, scenario_prefix=sc_token, out_link_path=None, network_type='base')

