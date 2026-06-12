#!/usr/bin/env python3
"""Probe page_1.pdf OCR blocks for cover tuning."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
PDF = r"C:\Users\paz\Desktop\P T W 测试\page_1.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\page_1_probe.json"

from volc_ocr import pdf_to_detail_image_mode, _normalize_text, _strip_watermark_substrings

details, pages_md = pdf_to_detail_image_mode(PDF)
page = details[0] if details else {}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"detail": page, "md": pages_md[0] if pages_md else ""}, f, ensure_ascii=False, indent=2)

print("blocks", len(page.get("textblocks") or []))
for i, b in enumerate(page.get("textblocks") or []):
    raw = (b.get("text") or "")[:80]
    norm = _normalize_text(b.get("text") or "")[:80]
    print(f"{i:02d} {b.get('label'):6s} box={b.get('box')} raw={raw!r} norm={norm!r}")