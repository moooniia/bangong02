#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

put(r"C:\Users\paz\Desktop\P T W 测试\page_6.pdf", "/tmp/page_6.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx, pdf_to_markdown, _detail_needs_image_mode, _detail_looks_fragmented, _doc_parse_image_only, _detail_has_usable_content, _meaningful_text_len, _STATIC_WATERMARKS

pdf = "/tmp/page_6.pdf"
md, details = pdf_to_markdown(pdf)
page = details[0] if details else {}
print("needs_image_mode", _detail_needs_image_mode(md, details))
print("looks_fragmented", _detail_looks_fragmented(page))
print("image_only", _doc_parse_image_only(md, details))
print("has_usable", _detail_has_usable_content(details))
print("meaningful", _meaningful_text_len(page, _STATIC_WATERMARKS))
print(volc_pdf_to_docx(pdf, "/tmp/page_6_out.docx"))
PY
"""
print(run(cmd, timeout=300)[1])
out = r"C:\Users\paz\Desktop\P T W 测试\page_6_out.docx"
fetch("/tmp/page_6_out.docx", out)
print("saved", out)