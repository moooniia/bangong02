#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

LOCAL_PDF = r"C:\Users\paz\Desktop\P T W 测试\page_1.pdf"
REMOTE_PDF = "/tmp/page_1.pdf"
LOCAL_OUT = r"C:\Users\paz\Desktop\P T W 测试\page_1_p2.docx"
LOCAL_PROBE = r"C:\Users\paz\Desktop\P T W 测试\page_1_probe.json"

put(LOCAL_PDF, REMOTE_PDF)

probe_cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import json, sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import pdf_to_detail_image_mode, _normalize_text
details, mds = pdf_to_detail_image_mode("/tmp/page_1.pdf")
page = details[0] if details else {}
with open("/tmp/page_1_probe.json", "w", encoding="utf-8") as f:
    json.dump({"detail": page, "md": mds[0] if mds else ""}, f, ensure_ascii=False, indent=2)
for i,b in enumerate(page.get("textblocks") or []):
    print(i, b.get("label"), _normalize_text(b.get("text") or "")[:70])
PY
"""
code, out, err = run(probe_cmd, timeout=180)
print(out or err)

convert_cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx
meta = volc_pdf_to_docx("/tmp/page_1.pdf", "/tmp/page_1_p2.docx")
print(meta)
PY
"""
code2, out2, err2 = run(convert_cmd, timeout=180)
print(out2 or err2)

fetch("/tmp/page_1_probe.json", LOCAL_PROBE)
fetch("/tmp/page_1_p2.docx", LOCAL_OUT)
print("saved", LOCAL_OUT, LOCAL_PROBE)