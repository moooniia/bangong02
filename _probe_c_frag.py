#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import pdf_to_markdown, _detail_looks_fragmented, _detail_needs_image_mode, _doc_parse_image_only
md, d = pdf_to_markdown("/tmp/C.pdf")
page = d[0] if d else {}
print("blocks", len(page.get("textblocks") or []))
print("frag", _detail_looks_fragmented(page))
print("image_only", _doc_parse_image_only(md, d))
print("needs", _detail_needs_image_mode(md, d))
PY
"""
print(run(cmd, timeout=120)[1])