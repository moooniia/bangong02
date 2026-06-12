#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
from volc_ocr import (
    _detect_dynamic_watermarks,
    _is_noise_text,
    _normalize_text,
    _meaningful_text_len,
)
from seal_utils import is_signature_page

CACHE = os.path.join(os.path.dirname(__file__), "1212_detail_full.json")
if not os.path.isfile(CACHE):
    CACHE = r"C:\Users\paz\toolbox-work\1212_detail_full.json"

with open(CACHE, encoding="utf-8") as f:
    pages = json.load(f)

wm = _detect_dynamic_watermarks(pages)
dropped = []
kept = 0
for pi, page in enumerate(pages):
    sig = is_signature_page(page, pi, len(pages))
    for b in page.get("textblocks") or []:
        lb = (b.get("label") or "para").lower()
        raw = (b.get("text") or "").strip()
        if not raw or lb in ("foot", "image"):
            continue
        norm = _normalize_text(raw)
        if lb == "header" and not norm.startswith("CMCCTD") and not __import__("re").fullmatch(r"\d{6,12}", norm):
            dropped.append((pi + 1, lb, raw[:60], "header_skip"))
            continue
        if _is_noise_text(norm, wm, sig_page=sig):
            dropped.append((pi + 1, lb, raw[:60], "noise"))
        else:
            kept += 1

print("kept_blocks", kept, "dropped", len(dropped))
for item in dropped[:25]:
    print(item)
print("...")
for item in dropped[-10:]:
    print(item)
print("meaningful per page:")
for pi, page in enumerate(pages):
    sig = is_signature_page(page, pi, len(pages))
    print(pi + 1, _meaningful_text_len(page, wm, sig_page=sig))