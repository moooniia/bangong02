import sys, traceback
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import _visual_service, _page_rgb_and_b64, _ocr_pdf_image_page_data, _preprocessed_ocr_path, _image_parse_dpi, pdf_page_count

pdf_path = "/tmp/A_test.pdf"
dpi = _image_parse_dpi()
print(f"DPI: {dpi}, pages: {pdf_page_count(pdf_path)}")

ocr_path, cleaned_tmp = _preprocessed_ocr_path(pdf_path)
visual = _visual_service()

for pi in range(pdf_page_count(pdf_path)):
    try:
        img_b64, _ = _page_rgb_and_b64(ocr_path, pi, dpi=dpi)
        result = _ocr_pdf_image_page_data(visual, img_b64)
        md = result.get("markdown") or ""
        print(f"  page{pi}: OK md_len={len(md)} preview={repr(md[:80])}")
    except Exception as e:
        print(f"  page{pi}: FAIL {e}")

import os
if cleaned_tmp and os.path.isfile(cleaned_tmp):
    os.unlink(cleaned_tmp)
