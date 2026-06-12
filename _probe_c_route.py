#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run

put(r"C:\Users\paz\Desktop\P T W 测试\C.pdf", "/tmp/C.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import pdf_to_markdown, _detail_needs_image_mode, _detail_has_usable_content, volc_pdf_to_docx
md, d = pdf_to_markdown("/tmp/C.pdf")
print("needs", _detail_needs_image_mode(md, d), "usable", _detail_has_usable_content(d))
print(volc_pdf_to_docx("/tmp/C.pdf", "/tmp/c.docx"))
PY
"""
print(run(cmd, timeout=180)[1])