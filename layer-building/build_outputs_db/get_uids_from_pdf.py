

from pathlib import Path
import PyPDF2 

def get_pdf_field_val(pdf_path, page_idx, field_delim, field_name):
    
    reader = PyPDF2.PdfReader(pdf_path)
    page = reader.pages[page_idx]
    pgtext = page.extract_text()
    pg_textlist = pgtext.split(field_delim)

    value_out = [i for i in pg_textlist if field_name in i][0].split(field_name)[1]

    return value_out


if __name__ == '__main__':
    pdf_dir = Path(r'C:\Users\dconly\Sacramento Area Council of Governments\PPA Development - General\PPA3\Development\Testing\reports with comments')

    field_del = '\n'
    fieldname = 'Project name ' # must include last character before value (e.g., space, colon, etc.)
    page_idx_val = 0 # 0 for first page, 1 for second page, etc.

    pdfs_list = [f for f in pdf_dir.glob("*.pdf")]
    # import pdb; pdb.set_trace()
    
    out_vals = []
    for pdf in pdfs_list:
        result = get_pdf_field_val(pdf_path=pdf, page_idx=page_idx_val, field_delim=field_del, field_name=fieldname)
        out_vals.append(result)

    print(out_vals)