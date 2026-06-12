#!/usr/bin/env python3
"""服务器端：优先火山 OCR，失败则用缓存 detail 转换。"""
import json
import os
import sys

sys.path.insert(0, "/home/toolbox/backend")
os.environ["TOOLBOX_ENV"] = "/home/toolbox/toolbox.env"

from volc_ocr import detail_to_docx, pdf_to_markdown, volc_configured, _docx_mode, pdf_page_count

PDF = "/tmp/1212.pdf"
CACHE = "/tmp/1212_detail_full.json"
OUT = "/tmp/1212_full.docx"


def main():
    details = None
    force = os.environ.get("FORCE_VOLC_OCR", "").strip().lower() in ("1", "true", "yes")
    if not force and os.path.isfile(CACHE):
        import time
        age = time.time() - os.path.getmtime(CACHE)
        if age < 3600:
            with open(CACHE, encoding="utf-8") as f:
                details = json.load(f)
            print("use recent cache", len(details), "pages", f"age={int(age)}s")
    if details is None and volc_configured():
        try:
            _, details = pdf_to_markdown(PDF)
            with open(CACHE, "w", encoding="utf-8") as f:
                json.dump(details, f, ensure_ascii=False)
            print("ocr fresh", len(details), "pages")
        except Exception as e:
            print("ocr failed", e)
    if details is None and os.path.isfile(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            details = json.load(f)
        print("use cache", len(details), "pages")
    if not details:
        raise SystemExit("no ocr data")
    mode = _docx_mode(pdf_page_count(PDF))
    detail_to_docx(details, OUT, pdf_path=PDF, mode=mode)
    print("saved", OUT)


if __name__ == "__main__":
    main()