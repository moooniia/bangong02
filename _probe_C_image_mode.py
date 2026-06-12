#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run

put(r"C:\Users\paz\Desktop\P T W 测试\C.pdf", "/tmp/C.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import _try_image_mode_docx, pdf_to_detail_image_mode, _detail_has_usable_content, pdf_to_markdown
pdf = "/tmp/C.pdf"
md, details = pdf_to_markdown(pdf)
try:
    print(_try_image_mode_docx(pdf, "/tmp/C_img.docx", md, details))
except Exception as e:
    print("image_mode_fail", e)
img_details, _ = pdf_to_detail_image_mode(pdf)
print("png usable", _detail_has_usable_content(img_details))
if img_details:
    p = img_details[0]
    print("png blocks", len(p.get("textblocks") or []))
    for b in (p.get("textblocks") or [])[:5]:
        print(" ", repr((b.get("text") or "")[:80]), b.get("label"))
PY
"""
print(run(cmd, timeout=180)[1])