"""
Re-OCR 1212.pdf with preprocessing enabled, fetch result back locally.
Consumes 12 Volc OCR pages.
"""
import os
import sys
import time
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run, put, fetch

PDF_LOCAL = r"C:\Users\paz\Desktop\1212\1212.pdf"
OUT_LOCAL = r"C:\Users\paz\Desktop\1212_fresh.docx"
CACHE_LOCAL = r"C:\Users\paz\toolbox-work\1212_detail_fresh.json"

print("=== Step 1: Upload PDF ===")
put(PDF_LOCAL, "/tmp/1212.pdf")
print("  uploaded")

print("\n=== Step 2: Force fresh OCR (preprocessing enabled) ===")
print("  running... (may take 60-120s)")
t0 = time.time()
cmd = """
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env FORCE_VOLC_OCR=1 python3.8 - <<'PYEOF'
import json, os, sys
sys.path.insert(0, "/home/toolbox/backend")
os.environ["TOOLBOX_ENV"] = "/home/toolbox/toolbox.env"
from volc_ocr import pdf_to_markdown, detail_to_docx, _docx_mode, pdf_page_count
PDF = "/tmp/1212.pdf"
print("OCR start...")
_, details = pdf_to_markdown(PDF)
with open("/tmp/1212_detail_full.json", "w", encoding="utf-8") as f:
    json.dump(details, f, ensure_ascii=False)
print(f"OCR done, {len(details)} pages")
mode = _docx_mode(pdf_page_count(PDF))
detail_to_docx(details, "/tmp/1212_full.docx", pdf_path=PDF, mode=mode)
print("saved /tmp/1212_full.docx", os.path.getsize("/tmp/1212_full.docx"), "bytes")
PYEOF
"""
code, out, err = run(cmd, timeout=300)
elapsed = int(time.time() - t0)
print(f"  exit={code}  {elapsed}s")
if out.strip():
    print("  STDOUT:", out.strip())
if err.strip():
    print("  STDERR:", err.strip()[:300])

if code != 0:
    sys.exit("OCR failed on server")

print("\n=== Step 3: Download Word and cache ===")
fetch("/tmp/1212_full.docx", OUT_LOCAL)
print(f"  Word: {OUT_LOCAL}  ({os.path.getsize(OUT_LOCAL)//1024} KB)")

try:
    fetch("/tmp/1212_detail_full.json", CACHE_LOCAL)
    print(f"  Cache: {CACHE_LOCAL}  ({os.path.getsize(CACHE_LOCAL)//1024} KB)")
except Exception as e:
    print(f"  Cache fetch skipped: {e}")

print("\nDone. Open 1212_fresh.docx to compare with previous output.")
