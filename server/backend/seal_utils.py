"""红色印章检测与透明底抠图。"""
import os

import cv2
import numpy as np

SEAL_EXTRACT_DPI = 180

_SIGNATURE_HINTS = (
    "签章", "签字", "盖章", "合同专用章", "签字/盖章", "专用章",
)


def red_mask(img_bgr, strict=False):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    sat_min = 90 if strict else 70
    val_min = 60 if strict else 50
    lower_red1 = np.array([0, sat_min, val_min])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, sat_min, val_min])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    if strict:
        return mask
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def _contour_score(cnt, bw, bh):
    area = cv2.contourArea(cnt)
    if area < 800:
        return 0.0
    perimeter = cv2.arcLength(cnt, True)
    if perimeter <= 0:
        return 0.0
    circularity = 4 * np.pi * area / (perimeter * perimeter)
    fill_ratio = area / float(max(bw * bh, 1))
    return circularity * 0.65 + fill_ratio * 0.35


def _make_seal_rgba(crop_bgr):
    """仅保留红色像素，去掉黑字/阴影，输出透明 PNG 数据。"""
    strict = red_mask(crop_bgr, strict=True)
    if cv2.countNonZero(strict) < 80:
        return None

    b, g, r = cv2.split(crop_bgr)
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    # 黑色文字/阴影：亮度低且红色饱和度不足
    dark_non_red = (gray < 95) & (strict == 0)
    alpha = strict.copy()
    alpha[dark_non_red] = 0

    alpha = cv2.erode(alpha, np.ones((2, 2), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

    vis = alpha > 0
    out_r = np.where(vis, np.maximum(r, 120), 0).astype(np.uint8)
    out_g = np.where(vis, np.minimum(g, (out_r * 0.35).astype(np.uint8)), 0).astype(np.uint8)
    out_b = np.where(vis, np.minimum(b, (out_r * 0.25).astype(np.uint8)), 0).astype(np.uint8)
    return cv2.merge([out_b, out_g, out_r, alpha])


def extract_red_seal(image_path, output_path):
    """整图抠红章，保留透明底。"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("无法读取图片")
    rgba = _make_seal_rgba(img)
    if rgba is None or cv2.countNonZero(rgba[:, :, 3]) < 200:
        raise ValueError("未检测到红色印章")
    cv2.imwrite(output_path, rgba)
    return output_path


def extract_red_seals_from_image(image_path, output_dir, min_area=2500, pad=8):
    """从页面图中检测多个红章区域，返回带坐标的透明 PNG 信息列表。"""
    img = cv2.imread(image_path)
    if img is None:
        return []

    h, w = img.shape[:2]
    mask = red_mask(img)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        area = bw * bh
        if area < min_area:
            continue
        short_side = min(bw, bh)
        if short_side < 70:
            continue
        if bw > w * 0.55 or bh > h * 0.55:
            continue
        ratio = bw / float(bh)
        if ratio < 0.6 or ratio > 1.7:
            continue
        score = _contour_score(cnt, bw, bh)
        min_score = 0.12 if area >= 12000 else 0.2
        if score < min_score:
            continue
        boxes.append((x, y, bw, bh, area, score, cnt))

    if not boxes:
        return []

    boxes.sort(key=lambda b: b[4], reverse=True)
    merged = []
    for box in boxes:
        x, y, bw, bh, area, score, cnt = box
        cx, cy = x + bw / 2, y + bh / 2
        dup = False
        for mx, my, mbw, mbh, _, _, _ in merged:
            mcx, mcy = mx + mbw / 2, my + mbh / 2
            if abs(cx - mcx) < min(bw, mbw) * 0.45 and abs(cy - mcy) < min(bh, mbh) * 0.45:
                dup = True
                break
        if not dup:
            merged.append(box)

    os.makedirs(output_dir, exist_ok=True)
    seals = []
    for i, (x, y, bw, bh, _, score, _) in enumerate(merged[:6]):
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + bw + pad)
        y1 = min(h, y + bh + pad)
        crop = img[y0:y1, x0:x1]
        crop_mask = mask[y0:y1, x0:x1]
        crop_area = max((x1 - x0) * (y1 - y0), 1)
        red_density = cv2.countNonZero(crop_mask) / float(crop_area)
        if cv2.countNonZero(crop_mask) < 500 or red_density < 0.07:
            continue
        rgba = _make_seal_rgba(crop)
        if rgba is None or cv2.countNonZero(rgba[:, :, 3]) < 200:
            continue
        out = os.path.join(output_dir, f"seal_{i}.png")
        cv2.imwrite(out, rgba)
        seals.append({
            "path": out,
            "x": x0,
            "y": y0,
            "w": x1 - x0,
            "h": y1 - y0,
            "cx": x0 + (x1 - x0) / 2.0,
            "cy": y0 + (y1 - y0) / 2.0,
            "score": score,
        })

    seals.sort(key=lambda s: (s["cy"], s["cx"]))
    return seals


def extract_signature_areas(img_bgr, ocr_blocks=None, min_area=1200, dpi=180, out_dir=None, pad=6):
    """
    Detect handwritten signature blobs on a signature page.

    Looks for dark non-red ink clusters that are NOT covered by OCR text blocks.
    Returns list of dicts: {path, x, y, w, h, cx, cy}.
    img_bgr: page image at `dpi` resolution.
    ocr_blocks: list of {"box": {"x0","y0","x1","y1"}} from OCR at the OCR DPI.
    out_dir: directory to write extracted PNGs; uses tempdir if None.
    """
    if img_bgr is None or img_bgr.size == 0:
        return []
    h, w = img_bgr.shape[:2]

    # Dark ink (black / dark blue) — exclude red stamp pixels
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)
    binary[red_mask(img_bgr) > 0] = 0

    # Build OCR text mask to suppress printed-text regions
    text_mask = np.zeros((h, w), dtype=np.uint8)
    for blk in (ocr_blocks or []):
        box = blk.get("box") or {}
        x0_ = int(box.get("x0") or 0)
        y0_ = int(box.get("y0") or 0)
        x1_ = int(box.get("x1") or 0)
        y1_ = int(box.get("y1") or 0)
        if x1_ > x0_ and y1_ > y0_:
            text_mask[y0_:y1_, x0_:x1_] = 255
    # Expand text mask slightly to absorb nearby stray pixels
    kernel = np.ones((7, 7), np.uint8)
    text_mask = cv2.dilate(text_mask, kernel, iterations=2)
    binary[text_mask > 0] = 0

    # Merge nearby strokes into blobs
    kernel2 = np.ones((9, 9), np.uint8)
    merged = cv2.dilate(binary, kernel2, iterations=3)

    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    page_area = h * w
    results = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        if area > 0.08 * page_area:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 25 or bh < 18:
            continue
        aspect = bw / float(bh)
        # Reject very elongated shapes (single text lines)
        if aspect > 7.0 or aspect < 0.12:
            continue
        # Reject very tall/narrow (single character column)
        fill = area / float(bw * bh)
        if fill > 0.80:
            continue
        # Must be in the lower half (signatures are at bottom of sig pages)
        cy_norm = (y + bh / 2.0) / h
        if cy_norm < 0.3:
            continue
        results.append((x, y, bw, bh, area))

    if not results:
        return []

    # Deduplicate overlapping boxes
    results.sort(key=lambda t: t[4], reverse=True)
    kept = []
    for box in results:
        x, y, bw, bh, _ = box
        cx_, cy_ = x + bw / 2.0, y + bh / 2.0
        dup = False
        for kx, ky, kbw, kbh, _ in kept:
            kcx, kcy = kx + kbw / 2.0, ky + kbh / 2.0
            if abs(cx_ - kcx) < min(bw, kbw) * 0.5 and abs(cy_ - kcy) < min(bh, kbh) * 0.5:
                dup = True
                break
        if not dup:
            kept.append(box)

    import tempfile
    if out_dir is None:
        out_dir = tempfile.mkdtemp(prefix="sig_")
    os.makedirs(out_dir, exist_ok=True)

    sigs = []
    for i, (x, y, bw, bh, _) in enumerate(kept[:4]):
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + bw + pad)
        y1 = min(h, y + bh + pad)
        crop = img_bgr[y0:y1, x0:x1]
        # Make transparent: keep dark pixels, white out the rest
        crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, alpha = cv2.threshold(crop_gray, 110, 255, cv2.THRESH_BINARY_INV)
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        b_ch = np.where(alpha > 0, np.minimum(crop[:, :, 0], 80), 255).astype(np.uint8)
        g_ch = np.where(alpha > 0, np.minimum(crop[:, :, 1], 80), 255).astype(np.uint8)
        r_ch = np.where(alpha > 0, np.minimum(crop[:, :, 2], 80), 255).astype(np.uint8)
        rgba = cv2.merge([b_ch, g_ch, r_ch, alpha])
        out = os.path.join(out_dir, f"sig_{i}.png")
        cv2.imwrite(out, rgba)
        sigs.append({
            "path": out,
            "x": x0, "y": y0,
            "w": x1 - x0, "h": y1 - y0,
            "cx": x0 + (x1 - x0) / 2.0,
            "cy": y0 + (y1 - y0) / 2.0,
        })

    sigs.sort(key=lambda s: (s["cy"], s["cx"]))
    return sigs


def page_text_blob(page):
    parts = []
    for block in page.get("textblocks") or []:
        text = (block.get("text") or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def is_signature_page(page, page_index, total_pages):
    text = page_text_blob(page)
    if not text:
        return page_index >= total_pages - 1

    if any(k in text for k in ("签章页", "(签章页)", "签字页", "(签字页)")):
        return True
    if any(h in text for h in ("签字/盖章", "合同专用章")):
        return page_index >= max(0, total_pages - 3)

    if page_index < max(0, total_pages - 2):
        return False

    has_party = "甲方" in text and "乙方" in text
    has_sign = any(k in text for k in ("日期", "盖章", "签字", "签章"))
    return has_party and has_sign