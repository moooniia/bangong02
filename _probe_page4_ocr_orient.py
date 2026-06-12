#!/usr/bin/env python3
"""Score page_4 at 4 rotations using quick OCR / line structure."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

PDF = r"C:\Users\paz\Desktop\P T W 测试\page_4.pdf"
import volc_ocr as vo

bgr = vo._render_page_bgr(PDF, 0, 150)

HINTS = ("考评打分表", "服务管理考评", "考评内容", "扣分标准", "序号", "分值", "备注", "小计", "合计")


def score_text(text):
    if not text:
        return 0.0
    hits = sum(1 for h in HINTS if h in text)
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return hits * 15 + min(cjk, 200) * 0.5


def line_structure_score(bgr):
    import cv2
    import numpy as np

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = binary.shape
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 30), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 30)))
    hlines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk)
    vlines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk)
    hsum = float(hlines.sum())
    vsum = float(vlines.sum())
    ratio = hsum / max(vsum, 1.0)
    # upright table: more horizontal lines than vertical (rows)
    return ratio


def tesseract_osd(bgr):
    try:
        import cv2
        import pytesseract
        from PIL import Image

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        osd = pytesseract.image_to_osd(pil, output_type=pytesseract.Output.DICT)
        return osd
    except Exception as e:
        return {"error": str(e)}


print("=== Per-rotation scores ===")
for deg in (0, 90, 180, 270):
    rot = vo._rotate_bgr(bgr, deg) if deg else bgr
    line_sc = line_structure_score(rot)
    osd = tesseract_osd(rot)
    osd_rot = osd.get("rotate", osd.get("error"))
    osd_conf = osd.get("orientation_conf", "")
    print(f"deg={deg}: line_h/v={line_sc:.2f} osd_rotate={osd_rot} conf={osd_conf}")

# Try volc quick on rotated png if configured
try:
    import base64
    import cv2

    visual = vo._visual_service()
    print("\n=== Volc quick OCR hint score (if available) ===")
    for deg in (0, 90, 180, 270):
        rot = vo._rotate_bgr(bgr, deg) if deg else bgr
        ok, buf = cv2.imencode(".png", rot)
        if not ok:
            continue
        b64 = base64.b64encode(buf.tobytes()).decode()
        try:
            data = vo._ocr_pdf_image_page_data(visual, b64)
            md = data.get("markdown") or ""
            print(f"deg={deg}: md_score={score_text(md):.1f} len={len(md)} head={md[:80]!r}")
        except Exception as e:
            print(f"deg={deg}: volc err {e}")
except Exception as e:
    print("volc skip:", e)