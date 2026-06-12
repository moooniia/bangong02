#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

put(r"C:\Users\paz\Desktop\P T W 测试\page_7.pdf", "/tmp/page_7.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx, pdf_to_markdown, _detail_needs_image_mode
pdf = "/tmp/page_7.pdf"
md, details = pdf_to_markdown(pdf)
print("needs_image_mode", _detail_needs_image_mode(md, details))
print(volc_pdf_to_docx(pdf, "/tmp/page_7_out.docx"))
PY
"""
print(run(cmd, timeout=300)[1])
out = r"C:\Users\paz\Desktop\P T W 测试\page_7_p3.docx"
fetch("/tmp/page_7_out.docx", out)
print("saved", out)