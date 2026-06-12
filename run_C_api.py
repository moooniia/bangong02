#!/usr/bin/env python3
"""Force API (Volc OCR) convert C.pdf to Word."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run, put, fetch

PDF_LOCAL = r"C:\Users\paz\Desktop\P T W 测试\C.pdf"
OUT_LOCAL = r"C:\Users\paz\Desktop\P T W 测试\C_api.docx"
REMOTE_PDF = "/tmp/C.pdf"
REMOTE_DOCX = "/tmp/C_api.docx"

print("=== Upload C.pdf ===")
put(PDF_LOCAL, REMOTE_PDF)
print("uploaded")

print("\n=== Volc OCR API -> Word ===")
t0 = time.time()
cmd = f"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import os, sys, time
sys.path.insert(0, "/home/toolbox/backend")
os.environ["TOOLBOX_ENV"] = "/home/toolbox/toolbox.env"
from volc_ocr import volc_configured, volc_pdf_to_docx

pdf = "{REMOTE_PDF}"
out = "{REMOTE_DOCX}"
print("volc_configured", volc_configured())
t0 = time.time()
mode = volc_pdf_to_docx(pdf, out)
elapsed = time.time() - t0
print("mode", mode)
print("elapsed_sec", round(elapsed, 1))
print("size_bytes", os.path.getsize(out))
PYEOF
"""
code, out, err = run(cmd, timeout=180)
elapsed = int(time.time() - t0)
print(f"exit={code} wall={elapsed}s")
print(out)
if err.strip():
    print("stderr:", err.strip()[:500])
if code != 0:
    sys.exit(1)

print("\n=== Download ===")
fetch(REMOTE_DOCX, OUT_LOCAL)
print("saved:", OUT_LOCAL)
print("size_kb:", round(os.path.getsize(OUT_LOCAL) / 1024, 1))