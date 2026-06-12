#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

from volc_ocr import (
    _detect_dynamic_watermarks,
    _editable_text_page,
    _meaningful_text_len,
    _page_has_table,
    _page_mainly_table,
    _page_table_quality,
    _page_watermark_heavy,
    _should_render_snapshot,
    pdf_to_markdown,
)
from seal_utils import is_signature_page

PDF = r"C:\Users\paz\Desktop\1212.pdf"

md, details = pdf_to_markdown(PDF)
wm = _detect_dynamic_watermarks(details)
print("watermarks sample:", sorted(wm)[:20], "count", len(wm))
for i, page in enumerate(details):
    sig = is_signature_page(page, i, len(details))
    mlen = _meaningful_text_len(page, wm)
    wm_heavy = _page_watermark_heavy(page, wm)
    editable = _editable_text_page(page, wm, sig)
    snap = _should_render_snapshot(page, wm, sig, "hybrid", PDF, i)
    has_tbl = _page_has_table(page)
    tq = _page_table_quality(page) if has_tbl else None
    mainly = _page_mainly_table(page) if has_tbl else False
    blocks = len(page.get("textblocks") or [])
    print(
        f"p{i+1}: blocks={blocks} sig={sig} wm_heavy={wm_heavy} "
        f"meaningful={mlen} editable={editable} snap={snap} "
        f"table={has_tbl} tq={tq} mainly_tbl={mainly}"
    )