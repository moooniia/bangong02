#!/usr/bin/env python3
"""Diagnose and convert page_6.pdf."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run, fetch

PDF = r"C:\Users\paz\Desktop\P T W 测试\page_6.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\page_6_out.docx"

put(PDF, "/tmp/page_6.pdf")
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import sys
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx, pdf_to_markdown, _detail_needs_image_mode, _get_pdf_page_image
from seal_utils import is_signature_page, page_text_blob, extract_red_seals_from_image, extract_signature_areas, SEAL_EXTRACT_DPI
import cv2

pdf = "/tmp/page_6.pdf"
md, details = pdf_to_markdown(pdf)
page = details[0]
print("needs_image_mode", _detail_needs_image_mode(md, details))
print("is_sig_page", is_signature_page(page, 0, 1))
text = page_text_blob(page)
print("text_len", len(text))
print("text_head", repr(text[:400]))

blocks = page.get("textblocks") or []
print("blocks", len(blocks))
for i, b in enumerate(blocks[:25]):
    t = (b.get("text") or "").strip()[:70]
    box = b.get("box") or {}
    print(f"  b{i}: {t!r} box={box.get('x0')},{box.get('y0')}-{box.get('x1')},{box.get('y1')}")

hi = _get_pdf_page_image(pdf, 0, "/tmp/p6probe", dpi=SEAL_EXTRACT_DPI)
img = cv2.imread(hi)
h, w = img.shape[:2]
print("img", w, h)

seals = extract_red_seals_from_image(hi, "/tmp/p6seals")
print("seals", len(seals))
for s in seals:
    print(" ", s["w"], s["h"], s["x"], s["y"])

page_hw = page.get("page_image_hw") or {}
ocr_w = page_hw.get("w") or w
ocr_h = page_hw.get("h") or h
sx, sy = w / float(ocr_w), h / float(ocr_h)
scaled = []
for blk in blocks:
    box = blk.get("box") or {}
    if not box:
        continue
    scaled.append({
        "box": {
            "x0": int((box.get("x0") or 0) * sx),
            "y0": int((box.get("y0") or 0) * sy),
            "x1": int((box.get("x1") or 0) * sx),
            "y1": int((box.get("y1") or 0) * sy),
        }
    })

sigs = extract_signature_areas(img, ocr_blocks=scaled, out_dir="/tmp/p6sigs", sig_page=True)
print("sigs_sig_page", len(sigs))
for s in sigs:
    print(" ", s["w"], s["h"], s["x"], s["y"])

print("convert", volc_pdf_to_docx(pdf, "/tmp/page_6_out.docx"))
PY
"""
code, out, err = run(cmd, timeout=300)
print(out)
if err:
    print("ERR", err)
print("exit", code)

fetch("/tmp/page_6_out.docx", OUT)
print("saved", OUT)