"""
Name: set_calendar_dates.py
Purpose: Hard codes in start_date and end_date values for calendar.txt files
    This is to ensure all operators' start and end dates are shared for regional analyses.

    NOTE - THIS WILL NOT WORK FOR YCTD. ITS DATES MUST BE UPDATED MANUALLY USING FOLLOWING PROCESS:
        1 - Use calendar_dates.txt to identify which service_ids correspond to normal weekday, normal Saturday, normal Sunday	
        2 - Create calendar.txt with following fields and apply correct values (even better, just have a template calendar.txt for YCTD and just update the service_id and start/end dates when new feed comes in	
                service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
        3 - Update calendar_dates.txt to:	
                only have 1 unique value in date field
                remove all rows with duplicate service_id values


Author: Darren Conly
Last Updated: Aug 2023
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path
import shutil
import pandas as pd
import csv
import zipfile

def update_start_end_dates(op_dir, file_name, new_start_date, new_end_date,
                           start_date_field, end_date_field, dummy_date):

    txt_file_in = Path(op_dir).joinpath(file_name)

    if txt_file_in.exists():
        dict_rows = []
        with open(txt_file_in, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for k, v in row.items():
                    row[k] = v.replace(',', '_') # prevent weird field delimiting issues by removing commas from field values
                dict_rows.append(row)

        # if gtfs_dir.name == 'ElDorado_0103_2020': 
        #     import pdb; pdb.set_trace()
        header = ','.join(dict_rows[0].keys())
        rows_out = [header]
        for dr in dict_rows:
            dr[start_date_field] = new_start_date
            dr[end_date_field] = new_end_date
            rowvals = ','.join(dr.values())
            rows_out.append(rowvals)

        with open(txt_file_in, 'w') as f:
            for row in rows_out:
                f.write(f"{row}\n")
        
        update_calendar_dates_txt(op_dir, dummy_date_str=dummy_date)
    else:
        if file_name == 'calendar.txt':
            print(f"\tWARNING: {txt_file_in} not found. You may need to manually update dates in calendar_dates.txt")
        pass


def update_calendar_dates_txt(op_dir, dummy_date_str):
    """hard-set all calendar_date date field vals to dummy_date_str
    and delete all rows with duplicate service_id values"""

    calendar_dates_txt = Path(op_dir).joinpath('calendar_dates.txt')

    df = pd.read_csv(calendar_dates_txt)

    df['date'] = dummy_date_str
    # import pdb; pdb.set_trace()

    df = df.groupby('service_id', as_index=False).min()


    header_out = ','.join(df.columns)
    with open(calendar_dates_txt, 'w') as fo:
        fo.write(f"{header_out}\n")
        for row in df.to_records(index=False):
            row = ','.join([str(i) for i in row])
            fo.write(f"{row}\n")


def create_zip(dir_to_zip, zip_parent_dir):
    
    fp_tozip = Path(dir_to_zip)
    fp_parentdir = Path(zip_parent_dir)
    out_zip_path = fp_parentdir.joinpath(f"{fp_tozip.name}.zip")
    with zipfile.ZipFile(out_zip_path, 'w') as zo:
        for f in fp_tozip.glob('*'):
            zo.write(f, arcname=f.name)

def extract_zip(zfile_in, output_folder=None, overwrite_ok=True):
    if not output_folder:
        zfp = Path(zfile_in)
        output_folder = zfp.parent.joinpath(zfp.stem)
    else:
        Path(output_folder).mkdir(exist_ok=overwrite_ok)

    with zipfile.ZipFile(zfile_in, 'r') as zfo:
        zfo.extractall(path=output_folder)

    return output_folder

if __name__ == '__main__':
    newstart = '20200101'
    newend = '20200601'

    dummy = '20200101' # set to some holiday value
    source_gtfs_parent_dir = r'I:\Projects\Darren\PEP\ConveyalData\ConveyalNetworkDevelopment\GTFS\2023-07-05 SACSIM base GTFS' # a folder containing only the ZIPs of GTFS feeds
    dest_gtfs_parent_dir = r'I:\Projects\Darren\PEP\ConveyalData\ConveyalNetworkDevelopment\GTFS\2023-07-05 SACSIM base GTFS\datemod_versions'


    # check = bool(input("WARNING: this script will overwrite calendar.txt. Enter 'yes' if you still wish to proceed. Otherwise leave blank and hit enter: "))
    # if not check:
    #     raise Exception("Script aborted by user.")
    
    for src_dir_zip in Path(source_gtfs_parent_dir).glob('*.zip'):

        # set up destination directory; deleting if already exists
        dest_dir = Path(dest_gtfs_parent_dir).joinpath(src_dir_zip.stem)
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        extract_zip(src_dir_zip, output_folder=dest_dir) # extract files to destination folder

        # shutil.copytree(src=src_dir, dst=dest_dir) # 1/12/24 - should be able to delete this line

        print(f"updating calendar.txt in {dest_dir}...")
        update_start_end_dates(op_dir=dest_dir, file_name='calendar.txt', 
                        new_start_date=newstart, new_end_date=newend,
                        start_date_field='start_date', end_date_field='end_date', 
                        dummy_date=dummy)
        
        print(f"updating feed_info.txt in {dest_dir}...")
        update_start_end_dates(op_dir=dest_dir, file_name='feed_info.txt', 
            new_start_date=newstart, new_end_date=newend,
            start_date_field='feed_start_date', end_date_field='feed_end_date', 
            dummy_date=dummy)
        create_zip(dest_dir, dest_gtfs_parent_dir)