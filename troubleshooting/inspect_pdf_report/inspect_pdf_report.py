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

from pathlib import Path
import os
import warnings as w
import datetime as dt

import pandas as pd
import PyPDF2 

from fgdb import ReportDatabase

class CoverPage:
    """Class to create object with all relevant data/attributes from the PDF report cover page"""
    def __init__(self, pdf_path, page_idx=0):
        reader = PyPDF2.PdfReader(pdf_path)
        page = reader.pages[page_idx]
        self.pgtext = page.extract_text()
        self.ptext_list = self.pgtext.split('\n')

        self.covpg_name = 'Title Report'

        # Tags used to know which field or part of PDF to refer to--
        # will need to have spaces converted to underlines for final table names?
        self.f_pname = 'Project name'
        self.f_jur = 'Jurisdiction'
        self.f_ptype = 'Project type'
        self.f_uid = 'Project UID'
        
        self.f_dt = 'Time Stamp'
        self.dtformat = '%A, %B %d, %Y %I:%M %p' # Example: 'Friday, January 20, 2023 03:01 PM'

        self.covpg_info = {}

        for f in [self.f_pname, self.f_jur, self.f_ptype, self.f_uid]:
            self.covpg_info[f] = self.get_val(f)

        creation_date = self.ptext_list[-1]
        self.covpg_info[self.f_dt] = self.report_dt_check(creation_date)

    def get_val(self, fname):
        entry = [e for e in self.ptext_list if fname in e][0]
        val = entry.replace(f"{fname} ", "")
        if val == entry: val = ''
        # if entry == 'Project UID': import pdb; pdb.set_trace()
        return val

    def report_dt_check(self, dt_string):
        # import pdb; pdb.set_trace()
        try:
            dts = dt.datetime.strptime(dt_string, self.dtformat)
            dt_string = dts.strftime('%Y-%m-%d %H:%M')
        except:
            warning = f"""Unable to parse report creation time stamp value
            {dt_string}. Please confirm this is the correct value."""

            w.warn(warning)
        
        return dt_string



def check_report(pdf, file_geodatabase):

    covpg = CoverPage(pdf)
    fgdb = ReportDatabase(file_geodatabase)

    project_uid = covpg.covpg_info[covpg.f_uid]
    project_type = covpg.covpg_info[covpg.f_ptype]

    successful_rpts = []
    failed_rpts = []

    out_dict = covpg.covpg_info

    if project_uid == '':
        out_dict['Successful Subrpts'] = "PROJECT LINE NOT SAVED TO DATABASE. ASK USER TO RE-RUN PROJECT"
        out_dict['Failed Subrpts'] = covpg.covpg_name
    else:
        perf_outcomes = fgdb.df_pmaster.loc[fgdb.df_pmaster[fgdb.f_uid] == project_uid][fgdb.f_poutcomes] \
            .values[0].split('; ')

        for po in perf_outcomes:
            subrpt_run = fgdb.check_subrpt_tbl(project_uid=project_uid, project_type=project_type, \
                perf_outcome=po)
            
            if subrpt_run is True:
                successful_rpts.append(po)
            elif subrpt_run is False:
                failed_rpts.append(po)
            else:
                print(subrpt_run) # this will come up if the project type-perf outcome combo weren't found in ReportDataBase.subrpt_dict

        out_dict['Successful Subrpts'] = '; '.join(successful_rpts)
        out_dict['Failed Subrpts'] = '; '.join(failed_rpts)

    return out_dict


if __name__ == '__main__':
    pdf_folder = r"C:\Users\dconly\Sacramento Area Council of Governments\PPA Development - General\PPA3\Development\Testing\reports_with_errors"


    fgdb = r'\\arcserver-svr\D\PPA3_SVR\PPA3_GIS_SVR\PPA3_run_data.gdb'

    #================RUN SCRIPT=======================================
    pdf_dir = Path(pdf_folder)
    pdfs_list = [f for f in pdf_dir.glob("*.pdf")]

    results_list = []
    for pdf_file in pdfs_list:
        report_results = check_report(pdf_file, fgdb)
        report_results["ReportFilePath"] = pdf_file
        results_list.append(report_results)

    df = pd.DataFrame(results_list)

    sufx = str(dt.datetime.now().strftime('%Y%m%d_%H%M'))
    output_csv = os.path.join(pdf_folder, f"report_inspection{sufx}.csv")
    df.to_csv(output_csv, index=False)

    print(f"Success! Inspection results in {output_csv}")