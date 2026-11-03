import json, sys, os
sys.path.insert(0, '/home/toolbox/backend')
os.chdir('/home/toolbox/backend')
PDF='/home/toolbox/uploads/1212.pdf'
CACHE='/home/toolbox/1212_detail_300dpi.json'
OUT='/home/toolbox/1212_v3.docx'
from volc_ocr import detail_to_docx, _docx_mode, pdf_page_count
details = json.load(open(CACHE, encoding='utf-8'))
mode = _docx_mode(pdf_page_count(PDF))
print('pages=%d mode=%s' % (len(details), mode))
detail_to_docx(details, OUT, pdf_path=PDF, mode=mode)
sz = os.path.getsize(OUT)
print('saved %s  %d KB' % (OUT, sz//1024))
