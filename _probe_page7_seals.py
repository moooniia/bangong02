#!/usr/bin/env python3
"""Diagnose seal/signature extraction on page_7."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
sys.path.insert(0, os.path.dirname(__file__))

from ssh_helper import put, run, fetch

put(r"C:\Users\paz\Desktop\P T W 测试\page_7.pdf", "/tmp/page_7.pdf")
OUT = r"C:\Users\paz\Desktop\P T W 测试\page_7_seal_probe"

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PY'
import os, sys, tempfile, json
import cv2
sys.path.insert(0, "/home/toolbox/backend")
from seal_utils import SEAL_EXTRACT_DPI, extract_red_seals_from_image, extract_signature_areas, red_mask
from volc_ocr import pdf_to_detail_image_mode, _get_pdf_page_image

details, _ = pdf_to_detail_image_mode("/tmp/page_7.pdf")
page = details[0]
os.makedirs("/tmp/p7probe", exist_ok=True)
hi = _get_pdf_page_image("/tmp/page_7.pdf", 0, "/tmp/p7probe", dpi=SEAL_EXTRACT_DPI)
img = cv2.imread(hi)
h, w = img.shape[:2]
print("img", w, h, hi)

# raw red contours
mask = red_mask(img)
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print("red_contours", len(contours))
for i, cnt in enumerate(sorted(contours, key=cv2.contourArea, reverse=True)[:12]):
    x, y, bw, bh = cv2.boundingRect(cnt)
    print(f"  c{i}: area={cv2.contourArea(cnt):.0f} box={bw}x{bh} @({x},{y})")

seal_dir = "/tmp/p7seals"
seals = extract_red_seals_from_image(hi, seal_dir)
print("seals_extracted", len(seals))
for s in seals:
    print(" ", s["w"], s["h"], s["x"], s["y"], s["path"])

page_hw = page.get("page_image_hw") or {}
ocr_w = page_hw.get("w") or w
ocr_h = page_hw.get("h") or h
sx, sy = w / float(ocr_w), h / float(ocr_h)
scaled = []
for blk in page.get("textblocks") or []:
    box = blk.get("box") or {}
    if not box:
        continue
    scaled.append({"box": {
        "x0": int((box.get("x0") or 0) * sx),
        "y0": int((box.get("y0") or 0) * sy),
        "x1": int((box.get("x1") or 0) * sx),
        "y1": int((box.get("y1") or 0) * sy),
    }})

sig_dir = "/tmp/p7sigs"
sigs = extract_signature_areas(img, ocr_blocks=scaled, out_dir=sig_dir, sig_page=True)
print("sigs_with_ocr_mask_sig_page", len(sigs))
for s in sigs:
    print(" ", s["w"], s["h"], s["x"], s["y"])

sigs2 = extract_signature_areas(img, ocr_blocks=[], out_dir="/tmp/p7sigs2")
print("sigs_no_mask", len(sigs2))
for s in sigs2:
    print(" ", s["w"], s["h"], s["x"], s["y"])

# save probe images list
with open("/tmp/p7_probe_list.json", "w") as f:
    json.dump({
        "seals": [{"p": s["path"], "w": s["w"], "h": s["h"]} for s in seals],
        "sigs": [{"p": s["path"], "w": s["w"], "h": s["h"]} for s in sigs],
        "sigs2": [{"p": s["path"], "w": s["w"], "h": s["h"]} for s in sigs2],
    }, f)
PY
"""
code, out, err = run(cmd, timeout=180)
print(out)
if err:
    print("ERR", err)
print("exit", code)

os.makedirs(OUT, exist_ok=True)
for remote, local in [
    ("/tmp/p7_probe_list.json", os.path.join(OUT, "list.json")),
]:
    try:
        fetch(remote, local)
    except Exception as e:
        print("fetch err", e)
print("done")