import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

PDF = r"C:\Users\paz\Desktop\P T W 测试\A.pdf"
put(PDF, "/tmp/A.pdf")

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import re, sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import pdf_to_markdown, pdf_to_markdown_image_mode, _markdown_has_usable_content, _doc_parse_image_only
from app import analyze_pdf

diag = analyze_pdf("/tmp/A.pdf")
print("DIAG", diag)

md, details = pdf_to_markdown("/tmp/A.pdf")
print("direct_md_len", len(md or ""))
print("direct_usable", _markdown_has_usable_content(md))
print("image_only", _doc_parse_image_only(md, details))
print("details_pages", len(details or []))
if md:
    print("direct_preview", repr((md or "")[:500]))
pages = pdf_to_markdown_image_mode("/tmp/A.pdf")
print("image_pages", len(pages))
for i, p in enumerate(pages[:3]):
    print("page", i, "len", len(p or ""))
    for ln in (p or "").split("\n")[:12]:
        print(" ", repr(ln[:120]))
PYEOF
"""
_, out, err = run(cmd, timeout=300)
print(out or err)