"""Generate final Word from the 300-DPI OCR cache."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
from volc_ocr import detail_to_docx, _docx_mode, pdf_page_count

PDF   = r"C:\Users\paz\Desktop\1212\1212.pdf"
CACHE = r"C:\Users\paz\toolbox-work\1212_detail_300dpi.json"
OUT   = r"C:\Users\paz\Desktop\1212_v2.docx"

details = json.load(open(CACHE, encoding="utf-8"))
mode = _docx_mode(pdf_page_count(PDF))
print(f"pages={len(details)}  mode={mode}")
detail_to_docx(details, OUT, pdf_path=PDF, mode=mode)
print(f"saved {OUT}  {os.path.getsize(OUT)//1024} KB")
