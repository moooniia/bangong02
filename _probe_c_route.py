#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run

put(r"C:\Users\paz\Desktop\P T W 测试\C.pdf", "/tmp/C.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import pdf_to_markdown, _detail_needs_image_mode, _detail_has_usable_content, _meaningful_text_len, _STATIC_WATERMARKS, volc_pdf_to_docx
pdf = "/tmp/C.pdf"
md, details = pdf_to_markdown(pdf)
print("pages", len(details))
for i, p in enumerate(details):
    print(i, "meaningful", _meaningful_text_len(p, _STATIC_WATERMARKS), "blocks", len(p.get("textblocks") or []))
print("needs_image", _detail_needs_image_mode(md, details))
print("has_usable", _detail_has_usable_content(details))
print(volc_pdf_to_docx(pdf, "/tmp/C_out.docx"))
PY
"""
print(run(cmd, timeout=180)[1])