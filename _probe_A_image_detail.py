import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import base64, json, sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import _visual_service, _page_rgb_and_b64, _meaningful_text_len, _STATIC_WATERMARKS
from preprocessing import preprocess_pdf_for_ocr

pdf = "/tmp/A.pdf"
clean = preprocess_pdf_for_ocr(pdf)
print("preprocess", clean != pdf, clean)

visual = _visual_service()
for pi in [0, 1, 6]:
    b64, _ = _page_rgb_and_b64(clean, pi, dpi=300)
    form = {
        "image_base64": b64,
        "version": "v3",
        "file_type": "image",
        "page_start": 0,
        "page_num": 1,
        "table_mode": "html",
        "filter_header": "true",
        "parse_mode": "auto",
    }
    resp = visual.ocr_pdf(form)
    data = resp.get("data") or {}
    detail = data.get("detail")
    if isinstance(detail, str):
        detail = json.loads(detail)
    md = (data.get("markdown") or "")[:200]
    pages = detail if isinstance(detail, list) else []
    print("page", pi, "md_len", len(data.get("markdown") or ""), "detail_pages", len(pages))
    if pages:
        p0 = pages[0]
        blocks = p0.get("textblocks") or []
        meaningful = _meaningful_text_len(p0, _STATIC_WATERMARKS)
        print("  blocks", len(blocks), "meaningful", meaningful, "hw", p0.get("page_image_hw"))
        for b in blocks[:8]:
            box = b.get("box") or {}
            t = (b.get("text") or "")[:60].replace("\n"," ")
            print("  ", b.get("label"), box.get("x0"), box.get("y0"), repr(t))
    print("  md", repr(md))
PYEOF
"""
_, out, err = run(cmd, timeout=180)
print(out or err)