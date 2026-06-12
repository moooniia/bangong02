#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run

put(r"C:\Users\paz\Desktop\P T W 测试\page_6.pdf", "/tmp/page_6.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import (
    pdf_to_markdown, pdf_to_detail_image_mode, pdf_to_markdown_image_mode,
    _detail_has_usable_content, _classify_scan_doc, _looks_like_task_checklist,
    _looks_like_contract, _meaningful_text_len, _STATIC_WATERMARKS,
)

pdf = "/tmp/page_6.pdf"
md, details = pdf_to_markdown(pdf)
page = details[0] if details else {}
print("direct meaningful", _meaningful_text_len(page, _STATIC_WATERMARKS))
print("direct blocks", len(page.get("textblocks") or []))
print("classify", _classify_scan_doc(pdf, md, details))
print("checklist", _looks_like_task_checklist(md, details))
print("contract", _looks_like_contract(md, details))

img_details, pages_md = pdf_to_detail_image_mode(pdf)
print("png detail pages", len(img_details), "usable", _detail_has_usable_content(img_details))
if img_details:
    p = img_details[0]
    print("png meaningful", _meaningful_text_len(p, _STATIC_WATERMARKS))
    print("png blocks", len(p.get("textblocks") or []))
    print("png tables", len(p.get("tables") or []))
    for i, b in enumerate((p.get("textblocks") or [])[:8]):
        print(" ", i, repr((b.get("text") or "")[:50]), b.get("label"))

pages_md2 = pdf_to_markdown_image_mode(pdf)
combined = "\n\n".join(pages_md2)
print("png md len", len(combined))
print("has table tag", "<table" in combined.lower())
print("md head", repr(combined[:400]))
PY
"""
print(run(cmd, timeout=300)[1])