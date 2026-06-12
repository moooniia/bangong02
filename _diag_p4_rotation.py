"""诊断 page_4.pdf 旋转检测：OSD / 墨迹指标 / 各角度得分。"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

import cv2
import numpy as np

PDF = r"C:\Users\paz\Desktop\P T W 测试\page_4.pdf"
DPI = 150

# 渲染
import fitz
doc = fitz.open(PDF)
page = doc[0]
mat = fitz.Matrix(DPI/72, DPI/72)
pix = page.get_pixmap(matrix=mat, alpha=False)
arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
doc.close()
print(f"PDF page rotation meta: {int(fitz.open(PDF)[0].rotation)}")
print(f"Rendered image: {bgr.shape[1]}w x {bgr.shape[0]}h px at {DPI} dpi")

# 保存渲染图供人眼看
out_img = r"C:\Users\paz\Desktop\P T W 测试\page_4_raw_150dpi.png"
cv2.imwrite(out_img, bgr)
print(f"Raw render saved: {out_img}")

# 墨迹指标
from volc_ocr import (
    _ink_cover_metrics, _has_sidebar_vertical_layout,
    _detect_visual_sideways_rotation, _orientation_combined_score,
    _rotate_bgr, _detect_fine_skew_deg,
)

cover = _ink_cover_metrics(bgr)
sidebar = _has_sidebar_vertical_layout(bgr)
print(f"\n--- 墨迹指标 ---")
print(f"  cover_w={cover['cover_w']:.3f}  cover_h={cover['cover_h']:.3f}  aspect={cover['aspect']:.3f}  portrait={cover['portrait']}")
print(f"  has_sidebar_vertical_layout: {sidebar}")
print(f"  detect_visual_sideways_rotation: {_detect_visual_sideways_rotation(bgr)}")

print(f"\n--- 四向得分 ---")
for deg in (0, 90, 180, 270):
    img = _rotate_bgr(bgr, deg)
    score = _orientation_combined_score(img)
    skew = _detect_fine_skew_deg(img)
    print(f"  {deg:3d}°: combined={score:.2f}  skew={skew:.2f}°")

# OSD
print(f"\n--- Tesseract OSD ---")
try:
    import pytesseract
    from PIL import Image
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    osd = pytesseract.image_to_osd(Image.fromarray(rgb), output_type=pytesseract.Output.DICT)
    print(f"  orientation_conf={osd.get('orientation_conf')}  rotate={osd.get('rotate')}  script={osd.get('script')}")
except Exception as e:
    print(f"  FAILED: {e}")
