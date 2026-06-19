import sys, traceback
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import _visual_service, _page_rgb_and_b64, _ocr_pdf_image_page_data, _preprocessed_ocr_path, _image_parse_dpi

pdf_path = "/tmp/A_test.pdf"
dpi = _image_parse_dpi()
print(f"DPI: {dpi}")

ocr_path, cleaned_tmp = _preprocessed_ocr_path(pdf_path)
print(f"ocr_path: {ocr_path}, cleaned: {cleaned_tmp}")

visual = _visual_service()

try:
    img_b64, _ = _page_rgb_and_b64(ocr_path, 0, dpi=dpi)
    print(f"img_b64 len: {len(img_b64)}")
    result = _ocr_pdf_image_page_data(visual, img_b64)
    print("SUCCESS, markdown len:", len(result.get("markdown","") or ""), "detail:", len(result.get("detail") or []))
except Exception as e:
    traceback.print_exc()
    print("ERROR:", e)

import os
if cleaned_tmp and os.path.isfile(cleaned_tmp):
    os.unlink(cleaned_tmp)
