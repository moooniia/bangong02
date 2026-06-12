#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run

put(r"C:\Users\paz\Desktop\P T W 测试\page_4.pdf", "/tmp/page_4.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import pdf_to_detail_image_mode, _page_is_dense_table, _page_is_dense_table as dense
from seal_utils import page_text_blob

pdf = "/tmp/page_4.pdf"
details, pages_md = pdf_to_detail_image_mode(pdf)
page = details[0]
print("png blocks", len(page.get("textblocks") or []))
for i,b in enumerate((page.get("textblocks") or [])[:15]):
    print(i, b.get("label"), repr((b.get("text") or "")[:80]))
print("page_md len", len(pages_md[0] if pages_md else ""))
print("dense", dense(page, pages_md[0] if pages_md else ""))
print("blob head", page_text_blob(page)[:300])
PY
"""
print(run(cmd, timeout=180)[1])