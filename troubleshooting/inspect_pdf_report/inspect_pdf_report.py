"""
Name: inspect_pdf_report.py
Purpose: Check PDF reports from PPA tool and see if they are missing report data or
    if, due to GP service failures, some or all of the tool outputs were not logged
    to the database.

    Desired outputs:
    •	Project name (from PDF)
    •	Jurisdiction (from PDF)
    •	Time created (from PDF)
    •	Project UID (from PDF; “not found” if not found)
    •	Project subreports requested (semicolon-separated list)
    •	Project subreports not logged (semicolon-separated list)



Author: Darren Conly
Last Updated: Jan 2023
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

import warnings as w
import datetime as dt

import PyPDF2 

class CoverPage:
    """Class to create object with all relevant data/attributes from the PDF report cover page"""
    def __init__(self, pdf_path, page_idx=0):
        reader = PyPDF2.PdfReader(pdf_path)
        page = reader.pages[page_idx]
        self.pgtext = page.extract_text()
        self.ptext_list = self.pgtext.split('\n')

        # Tags used to know which field or part of PDF to refer to--
        # will need to have spaces converted to underlines for final table names?
        self.f_pname = 'Project name'
        self.f_jur = 'Jurisdiction'
        self.f_ptype = 'Project type'
        self.f_uid = 'Project UID'
        
        self.f_dt = 'Time Stamp'
        self.dtformat = '%A, %B %d, %Y %I:%M %p' # Example: 'Friday, January 20, 2023 03:01 PM'

        self.out_dict = {}

        for f in [self.f_pname, self.f_jur, self.f_ptype, self.f_uid]:
            self.out_dict[f] = self.get_val(f)

        creation_date = self.ptext_list[-1]
        self.out_dict[self.f_dt] = self.report_dt_check(creation_date)

    def get_val(self, fname):
        entry = [e for e in self.ptext_list if fname in e][0]
        val = entry.replace(f"{fname} ", "")
        return val

    def report_dt_check(self, dt_string):
        try:
            dt.datetime.strptime(self.f_dt, self.dtformat)
        except:
            warning = f"""Unable to parse report creation time stamp value
            {dt_string}. Please confirm this is the correct value."""

            w.warn(warning)
        
        return dt_string



def get_pdf_field_val(pdf_path, page_idx, field_delim=None, field_name=None):
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

    import pdb; pdb.set_trace()
    pg_textlist = pgtext.split(field_delim)

    

    value_out = [i for i in pg_textlist if field_name in i][0].split(field_name)[1]

    return value_out




if __name__ == '__main__':
    pdf_file = r"C:\Users\dconly\Sacramento Area Council of Governments\PPA Development - General\PPA3\Development\Testing\reports_with_errors\fwy_all_noerrors.pdf"
    page_ival = 0

    get_pdf_field_val(pdf_file, page_ival)