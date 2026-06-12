#!/usr/bin/env python3
"""本地先测 ocr_utils，再部署后测线上。"""
import os
import sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work\server\backend")
from ocr_utils import ocr_image, clean_ocr_text

p = r"C:\Users\paz\Desktop\1.png"
if os.path.exists(p):
    t = ocr_image(p)
    print("=== FIXED LOCAL ===")
    print(t[:800])
    print("...")
    print("chars:", len(t))
    compact = __import__('re').sub(r'\s+', '', t)
    cjk = sum(1 for c in compact if '\u4e00' <= c <= '\u9fff')
    print("cjk ratio:", cjk / max(len(compact), 1))