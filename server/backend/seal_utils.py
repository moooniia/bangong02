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
    h, sat, val = cv2.split(hsv)

    # A stamp photo often contains pale red antialiasing and dark red ink over text.
    # HSV alone drops those pixels, so combine hue with RGB red dominance.
    b, g, r = [c.astype(np.int16) for c in cv2.split(img_bgr)]
    red_over_green = r - g
    red_over_blue = r - b

    if strict:
        sat_min = 82
        val_min = 45
        hue_red = (((h <= 12) | (h >= 168)) & (sat >= sat_min) & (val >= val_min))
        dominance = (r >= 55) & (red_over_green >= 16) & (red_over_blue >= 12)
        mask = (hue_red | (dominance & (sat >= 45))).astype(np.uint8) * 255
        return mask

    hue_red = (((h <= 16) | (h >= 162)) & (sat >= 28) & (val >= 35))
    orange_red = ((h <= 22) & (sat >= 40) & (val >= 45))
    dominance = (r >= 48) & (red_over_green >= 10) & (red_over_blue >= 8)
    strong_dominance = (r >= 60) & (red_over_green >= 18) & (red_over_blue >= 14)
    mask = ((hue_red & dominance) | (orange_red & dominance) | strong_dominance).astype(np.uint8) * 255

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
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
    """Extract red stamp pixels into a transparent PNG while preserving thin strokes."""
    strict = red_mask(crop_bgr, strict=True)
    broad = red_mask(crop_bgr, strict=False)
    if cv2.countNonZero(strict) < 40 and cv2.countNonZero(broad) < 120:
        return None

    b8, g8, r8 = cv2.split(crop_bgr)
    b = b8.astype(np.int16)
    g = g8.astype(np.int16)
    r = r8.astype(np.int16)
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    h, sat8, val8 = cv2.split(hsv)

    red_delta = np.minimum(r - g, r - b)
    max_delta = np.maximum(r - g, r - b)
    red_hue = ((h <= 18) | (h >= 160))

    # Include weak/low-contrast red ink, but reject neutral dark printed text behind it.
    candidate = (broad > 0) | (
        red_hue &
        (r >= 45) &
        (red_delta >= 7) &
        ((sat8 >= 22) | (max_delta >= 18))
    )
    neutral_dark_text = (gray < 105) & (red_delta < 12) & (sat8 < 75)
    candidate[neutral_dark_text] = False

    mask = candidate.astype(np.uint8) * 255
    if cv2.countNonZero(mask) < 80:
        return None

    # Bridge tiny gaps from paper texture without eating fine characters.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)

    # Drop isolated speckles only; stamp glyph dots and broken strokes are usually larger than this.
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    cleaned = np.zeros_like(mask)
    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= 3:
            cleaned[labels == i] = 255
    mask = cleaned

    sat = sat8.astype(np.float32)
    val = val8.astype(np.float32)
    strength_delta = np.clip((red_delta.astype(np.float32) - 4.0) / 36.0, 0.0, 1.0)
    strength_sat = np.clip((sat - 18.0) / 95.0, 0.0, 1.0)
    strength_val = np.clip((val - 28.0) / 85.0, 0.0, 1.0)
    alpha_f = np.maximum(strength_delta, strength_sat * 0.85) * np.maximum(strength_val, 0.38)
    alpha = np.where(mask > 0, np.clip(55 + alpha_f * 200, 0, 255), 0).astype(np.uint8)

    # Smooth alpha edges, then restore solid cores so the result is readable at normal size.
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    alpha[strict > 0] = np.maximum(alpha[strict > 0], 210)

    vis = alpha > 0
    out_r = np.where(vis, np.maximum(r8, 135), 0).astype(np.uint8)
    out_g = np.where(vis, np.minimum(g8, np.maximum(24, (out_r * 0.36).astype(np.uint8))), 0).astype(np.uint8)
    out_b = np.where(vis, np.minimum(b8, np.maximum(18, (out_r * 0.24).astype(np.uint8))), 0).astype(np.uint8)
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


def _red_seal_cluster_boxes(mask, min_red_pixels=1800, min_short_side=88):
    """膨胀连通红区，把圆环章+五角星合成一个框（避免只抠到星）。"""
    h, w = mask.shape[:2]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (23, 23))
    merged_mask = cv2.dilate(mask, kernel, iterations=2)
    merged_mask = cv2.morphologyEx(
        merged_mask, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)), iterations=2,
    )
    contours, _ = cv2.findContours(merged_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        short_side = min(bw, bh)
        if short_side < min_short_side:
            continue
        if bw > w * 0.55 or bh > h * 0.55:
            continue
        ratio = bw / float(max(bh, 1))
        if ratio < 0.55 or ratio > 1.85:
            continue
        crop = mask[y:y + bh, x:x + bw]
        red_px = cv2.countNonZero(crop)
        if red_px < min_red_pixels:
            continue
        boxes.append((x, y, bw, bh, red_px))
    boxes.sort(key=lambda b: b[4], reverse=True)
    return boxes


def _dedupe_boxes(boxes, overlap=0.42):
    merged = []
    for x, y, bw, bh, weight in boxes:
        cx, cy = x + bw / 2.0, y + bh / 2.0
        dup = False
        for mx, my, mbw, mbh, _ in merged:
            mcx, mcy = mx + mbw / 2.0, my + mbh / 2.0
            if abs(cx - mcx) < min(bw, mbw) * overlap and abs(cy - mcy) < min(bh, mbh) * overlap:
                dup = True
                break
        if not dup:
            merged.append((x, y, bw, bh, weight))
    return merged


def _prune_seal_star_fragments(seals, min_short=200, near_px=220):
    """去掉大章旁边误检的五角星/红字小碎片。"""
    if len(seals) <= 1:
        return seals
    big = [s for s in seals if min(s["w"], s["h"]) >= min_short]
    if not big:
        return seals
    kept = []
    for s in seals:
        if min(s["w"], s["h"]) >= min_short:
            kept.append(s)
            continue
        near_big = False
        for b in big:
            if abs(s["cx"] - b["cx"]) < near_px and abs(s["cy"] - b["cy"]) < near_px:
                near_big = True
                break
        if not near_big:
            kept.append(s)
    return kept if kept else seals


def extract_red_seals_from_image(image_path, output_dir, min_area=2500, pad=8):
    """从页面图中检测多个红章区域，返回带坐标的透明 PNG 信息列表。"""
    img = cv2.imread(image_path)
    if img is None:
        return []

    h, w = img.shape[:2]
    mask = red_mask(img)

    cluster_boxes = _red_seal_cluster_boxes(mask)
    contour_boxes = []
    if not cluster_boxes:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
            min_score = 0.08 if area >= 12000 else 0.12
            if score < min_score:
                continue
            contour_boxes.append((x, y, bw, bh, int(area * max(score, 0.1))))

    boxes = _dedupe_boxes(cluster_boxes + contour_boxes)
    if not boxes:
        return []

    os.makedirs(output_dir, exist_ok=True)
    seals = []
    for i, (x, y, bw, bh, _) in enumerate(boxes[:6]):
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
            "score": 1.0,
        })

    seals = _prune_seal_star_fragments(seals)
    seals.sort(key=lambda s: (s["cy"], s["cx"]))
    return seals


def extract_signature_areas(
    img_bgr, ocr_blocks=None, min_area=900, dpi=180, out_dir=None, pad=6, sig_page=False,
):
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

    # 印刷体遮罩：签章页只遮上半页条款区，避免甲乙方大块 OCR 框抹掉手写签名
    text_mask = np.zeros((h, w), dtype=np.uint8)
    for blk in (ocr_blocks or []):
        box = blk.get("box") or {}
        x0_ = int(box.get("x0") or 0)
        y0_ = int(box.get("y0") or 0)
        x1_ = int(box.get("x1") or 0)
        y1_ = int(box.get("y1") or 0)
        if x1_ <= x0_ or y1_ <= y0_:
            continue
        if sig_page and ((y0_ + y1_) / 2.0) > h * 0.44:
            continue
        text_mask[y0_:y1_, x0_:x1_] = 255
    kernel = np.ones((5, 5), np.uint8)
    text_mask = cv2.dilate(text_mask, kernel, iterations=1 if sig_page else 2)
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
        if cy_norm < (0.28 if sig_page else 0.3):
            continue
        if sig_page and aspect > 5.5:
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
    max_sigs = 3 if sig_page else 4
    for i, (x, y, bw, bh, _) in enumerate(kept[:max_sigs]):
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
        if total_pages <= 1:
            return False
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