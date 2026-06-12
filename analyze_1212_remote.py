import json
import os
import sys

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