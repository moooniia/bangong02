#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ssh_helper.py"))
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

REMOTE = "/tmp/analyze_1212.py"
LOCAL_OUT = os.path.join(os.path.dirname(__file__), "1212_detail_full.json")

SCRIPT = r'''
import json, os, sys
sys.path.insert(0, "/home/toolbox/backend")
os.environ["TOOLBOX_ENV"] = "/home/toolbox/toolbox.env"
from volc_ocr import pdf_to_markdown
pdf = "/tmp/1212.pdf"
md, details = pdf_to_markdown(pdf)
out = {"pages": len(details), "items": []}
for i, p in enumerate(details):
    blocks = p.get("textblocks") or []
    hw = p.get("page_image_hw") or {}
    labels = {}
    text_len = 0
    has_table = has_img = False
    sample = []
    for b in blocks:
        lb = b.get("label") or "para"
        labels[lb] = labels.get(lb, 0) + 1
        t = (b.get("text") or "").strip()
        if "<table" in t.lower():
            has_table = True
        if lb == "image" or b.get("url"):
            has_img = True
        if lb not in ("header", "foot") and t and len(sample) < 2:
            sample.append(t[:80])
        if lb not in ("header", "foot"):
            text_len += len(t)
    out["items"].append({
        "page": i + 1,
        "blocks": len(blocks),
        "text_len": text_len,
        "has_table": has_table,
        "has_img": has_img,
        "landscape": (hw.get("w") or 0) > (hw.get("h") or 0),
        "hw": hw,
        "labels": labels,
        "sample": sample,
    })
with open("/tmp/1212_detail_full.json", "w", encoding="utf-8") as f:
    json.dump(details, f, ensure_ascii=False)
with open("/tmp/1212_page_summary.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=2))
'''

put(r"C:\Users\paz\Desktop\1212.pdf", "/tmp/1212.pdf")
with open(REMOTE.replace("/tmp/analyze_1212.py", "analyze_1212_remote.py"), "w", encoding="utf-8") as f:
    f.write(SCRIPT)
put(os.path.join(os.path.dirname(__file__), "analyze_1212_remote.py"), REMOTE)
code, out, err = run(f"python3.8 {REMOTE}", timeout=180)
print(out or err)
fetch("/tmp/1212_detail_full.json", LOCAL_OUT)