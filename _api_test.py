import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import _visual_service, _page_rgb_and_b64, _ocr_pdf_image_page_data
import traceback
try:
    visual = _visual_service()
    img_b64, _ = _page_rgb_and_b64("/home/toolbox/fixtures/2.pdf", 0, dpi=150)
    result = _ocr_pdf_image_page_data(visual, img_b64)
    print("SUCCESS, markdown len:", len(result.get("markdown","") or ""))
except Exception as e:
    traceback.print_exc()
    print("ERROR:", e)
