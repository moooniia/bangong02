#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

put(r"C:\Users\paz\Desktop\P T W 测试\page_1.pdf", "/tmp/page_1.pdf")
convert_cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx
print(volc_pdf_to_docx("/tmp/page_1.pdf", "/tmp/page_1_p2.docx"))
PY
"""
print(run(convert_cmd, timeout=180)[1])
out = r"C:\Users\paz\Desktop\P T W 测试\page_1_p2_v096.docx"
fetch("/tmp/page_1_p2.docx", out)
print("saved", out)