#!/usr/bin/env python3
"""Diagnose and convert page_4.pdf."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

PDF = r"C:\Users\paz\Desktop\P T W 测试\page_4.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\page_4_out.docx"

put(PDF, "/tmp/page_4.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import (
    volc_pdf_to_docx, pdf_to_markdown, _detail_needs_image_mode,
    _detail_has_usable_content, _meaningful_text_len, _STATIC_WATERMARKS,
    _analyze_page_layout, _page_is_dense_table,
)
from seal_utils import is_signature_page, page_text_blob

pdf = "/tmp/page_4.pdf"
md, details = pdf_to_markdown(pdf)
page = details[0] if details else {}
print("needs_image_mode", _detail_needs_image_mode(md, details))
print("has_usable", _detail_has_usable_content(details))
print("meaningful", _meaningful_text_len(page, _STATIC_WATERMARKS))
print("is_sig_page", is_signature_page(page, 0, 1))
print("dense_table", _page_is_dense_table(page, page_md=""))
layout = _analyze_page_layout(pdf, 0, 180, probe_coarse=True)
print("layout", layout.get("kind"), "coarse", layout.get("correction_deg"), "skew", layout.get("skew_deg"))
text = page_text_blob(page)
print("text_len", len(text))
print("text_head", repr(text[:500]))
blocks = page.get("textblocks") or []
print("blocks", len(blocks))
for i, b in enumerate(blocks[:20]):
    t = (b.get("text") or "").strip()[:70]
    box = b.get("box") or {}
    print(f"  b{i}: {b.get('label')!r} {t!r} box={box.get('x0')},{box.get('y0')}-{box.get('x1')},{box.get('y1')}")
print("convert", volc_pdf_to_docx(pdf, "/tmp/page_4_out.docx"))
PY
"""
code, out, err = run(cmd, timeout=300)
print(out)
if err:
    print("ERR", err)
print("exit", code)

fetch("/tmp/page_4_out.docx", OUT)
print("saved", OUT)