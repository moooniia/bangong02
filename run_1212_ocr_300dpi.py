"""Re-OCR with PREPROCESS_DPI=300 to see if p11 table structure recovers."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run, fetch

print("Running OCR at 300 DPI...")
cmd = """
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env FORCE_VOLC_OCR=1 PREPROCESS_DPI=300 python3.8 - <<'PYEOF'
import json, os, sys
sys.path.insert(0, "/home/toolbox/backend")
os.environ["TOOLBOX_ENV"] = "/home/toolbox/toolbox.env"
os.environ["PREPROCESS_DPI"] = "300"
from volc_ocr import pdf_to_markdown, detail_to_docx, _docx_mode, pdf_page_count
PDF = "/tmp/1212.pdf"
print("OCR start (300 DPI)...")
_, details = pdf_to_markdown(PDF)
with open("/tmp/1212_detail_300.json", "w", encoding="utf-8") as f:
    json.dump(details, f, ensure_ascii=False)
print(f"done {len(details)} pages")
PYEOF
"""
t0 = time.time()
code, out, err = run(cmd, timeout=300)
print(f"exit={code}  {int(time.time()-t0)}s")
if out.strip(): print("OUT:", out.strip())
if err.strip(): print("ERR:", err.strip()[:200])
if code != 0:
    sys.exit("failed")

fetch("/tmp/1212_detail_300.json", "1212_detail_300dpi.json")
data = json.load(open("1212_detail_300dpi.json", encoding="utf-8"))

# Check p04 and p11
print("\n=== DPI=300 result ===")
for i, p in enumerate(data):
    blocks = p.get("textblocks", [])
    total = sum(len((b.get("text") or "").strip()) for b in blocks if (b.get("label") or "") != "foot")
    has_table = any("<table" in (b.get("text") or "").lower() for b in blocks)
    changed = ""
    if i == 3 and has_table: changed = " ← p04 table OK"
    if i == 10 and has_table: changed = " ← p11 table OK ✓"
    if i == 10 and not has_table: changed = " ← p11 table STILL MISSING ✗"
    print(f"  p{i+1:02d}: {len(blocks)} blocks  {total} chars  table={'YES' if has_table else '-'}{changed}")
