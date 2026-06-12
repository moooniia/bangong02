import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import json, sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import pdf_to_markdown, _detail_has_usable_content, _markdown_has_usable_content, _doc_parse_image_only, _meaningful_text_len, _STATIC_WATERMARKS

md, details = pdf_to_markdown("/tmp/A.pdf")
print("md_usable", _markdown_has_usable_content(md))
print("detail_usable", _detail_has_usable_content(details))
print("image_only", _doc_parse_image_only(md, details))
print("pages", len(details))
for pi, page in enumerate(details):
    blocks = page.get("textblocks") or []
    meaningful = _meaningful_text_len(page, _STATIC_WATERMARKS)
    raw = sum(len((b.get("text") or "").strip()) for b in blocks)
    labels = {}
    for b in blocks:
        lb = (b.get("label") or "para").lower()
        labels[lb] = labels.get(lb, 0) + 1
    print(f"page{pi}: blocks={len(blocks)} raw={raw} meaningful={meaningful} labels={labels}")
    for b in blocks[:6]:
        t = (b.get("text") or "")[:80].replace("\n"," ")
        print(" ", b.get("label"), repr(t))
PYEOF
"""
_, out, err = run(cmd, timeout=180)
print(out or err)