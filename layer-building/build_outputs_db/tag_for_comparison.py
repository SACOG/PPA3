"""
Name: tag_for_comparison.py
Purpose: Many PPA runs that are logged will be test runs or erroneous.
    For comparing in charts, we must omit these runs and only include "real" runs,
    defined as runs where the user emails their PDF report to SACOG.

    This report scans through a folder of PDF reports, gets the UID from the PDF, then
    in the project master table sets a "for_review" flag to 1, so that in charts we can filter
    to only include in the charts projects with for_review=1, to avoid cluttering the chart with erroneous runs.


Author: Darren Conly
Last Updated: Nov 2022
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

from pathlib import Path

import arcpy
import PyPDF2 

def get_pdf_field_val(pdf_path, page_idx, field_delim, field_name):
    """
    Args:
        pdf_path (_type_): path to pdf file
        page_idx (_type_): page of PDF to pull text from (first page is 0)
        field_delim (_type_): separator between different fields on the PDF document
        field_name (_type_): name of field whose value you want to retrieve. must include last character before value (e.g., space, colon, etc.).

    Returns: list of project UIDs from PDFs in folder. These UIDs will have their review flag updated in
    project master table
    """
    
    reader = PyPDF2.PdfReader(pdf_path)
    page = reader.pages[page_idx]
    pgtext = page.extract_text()
    pg_textlist = pgtext.split(field_delim)

    value_out = [i for i in pg_textlist if field_name in i][0].split(field_name)[1]

    return value_out

def update_review_flag(master_fc, pdf_dir, setval=1):
    """
    master_fc = PPA project master table with all project lines saved from all tool runs
    pdf_dir = folder of PDFs you want to iterate through and grab UID values from
    setval = for uids that are in the PDFs, find these UIDs in master_fc and set their value to this.
    
    """

    # pdf_doc_parameters
    pdf_field_del = '\n'
    pdf_fieldname = 'Project UID ' # must include last character before value (e.g., space, colon, etc.)
    pdf_page_idx_val = 0 # 0 for first page, 1 for second page, etc.
    
    # retrieve list of UIDs from PDFs
    pdfs_list = [f for f in pdf_dir.glob("*.pdf")]
    uid_list = {}
    for pdf in pdfs_list:
        result = get_pdf_field_val(pdf_path=pdf, page_idx=pdf_page_idx_val, 
                                    field_delim=pdf_field_del, field_name=pdf_fieldname)
        uid_list[result] = pdf


    # then, in master_fc, set the "for_revew" flag to setval if the UID is in the list generated from PDF parsing.
    f_master_uid = 'project_uid'
    f_master_revflag = 'for_review'

    fieldlist = [f_master_uid, f_master_revflag]
    uids_from_master = []
    cnt = 0
    with arcpy.da.UpdateCursor(master_fc, fieldlist) as cur:
        for row in cur:
            puid = row[fieldlist.index(f_master_uid)]

            if puid in uid_list.keys():
                row[fieldlist.index(f_master_revflag)] = setval
                cur.updateRow(row)
                cnt += 1

            uids_from_master.append(puid)

    arcpy.AddMessage(f"{cnt} out of {len(uid_list.keys())} PDFs had {f_master_revflag} set to {setval} in {master_fc}.")

    # check in case any of the UIDs in the PDFs is not in the master table
    uids_not_in_master = [pdf for uid, pdf in uid_list.items() if uid not in uids_from_master]
    if len(uids_not_in_master) > 0:
        arcpy.AddMessage(f"""The following PDFs did not have their project UID in {master_fc}:
            {uids_not_in_master}""")

"""
OVERALL PROCESS:
1 - scan through folder of PDFS, return list of project UIDs
2 - use UpdateCursor on project_master table:
    > if row UID value is in the list of project UIDs from step 1, then set row include_in_report value = 1 (i.e., yes include in report)
    >>>can also have "undo" version of function, i.e., can set value to zero if it's in the list!

"""


if __name__ == '__main__':
    pdf_folder = Path(r'C:\Users\dconly\Desktop\TempLocalPPA\TestPDFOutputs')

    master_fc_table = r'\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb\project_master'
    set_value = 1

    update_review_flag(master_fc=master_fc_table, pdf_dir=pdf_folder, setval=set_value)