#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

from volc_ocr import detail_to_docx, _docx_mode, pdf_page_count

PDF = r"C:\Users\paz\Desktop\1212.pdf"
CACHE = os.path.join(os.path.dirname(__file__), "1212_detail_full.json")
OUT = r"C:\Users\paz\Desktop\1212_full.docx"


def main():
    with open(CACHE, encoding="utf-8") as f:
        details = json.load(f)
    mode = _docx_mode(pdf_page_count(PDF))
    print("pages", len(details), "mode", mode)
    detail_to_docx(details, OUT, pdf_path=PDF, mode=mode)
    print("saved", OUT, "size", os.path.getsize(OUT))


if __name__ == "__main__":
    main()