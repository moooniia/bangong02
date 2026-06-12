"""
Pre-OCR image preprocessing for scanned PDF contracts.

Removes diagonal light-gray watermarks from scanned pages before OCR,
significantly improving text recognition quality on watermarked documents.

Environment variables:
  PREPROCESS_WATERMARK  1/0  Enable/disable watermark removal (default: 1)
  PREPROCESS_DPI        int  DPI for PDF-to-image conversion (default: 250)
  PREPROCESS_SENSITIVITY float  Watermark detection sensitivity 0.2–0.6 (default: 0.35)
"""
import os
import tempfile

import cv2
import numpy as np


def is_enabled():
    return os.environ.get("PREPROCESS_WATERMARK", "1").strip().lower() not in ("0", "false", "no")


def remove_light_watermark(img_bgr, sensitivity=0.35):
    """
    Remove diagonal light-gray watermarks from a scanned page image.

    The algorithm distinguishes three pixel zones by grayscale value:
      - Background (very bright, > ~220): keep as-is
      - Watermark (medium gray, in the "sensitivity gap"): replace with white
      - Text / dark content (dark, < ~120): keep as-is

    Colored pixels (red stamps, blue ink) are always preserved.

    sensitivity: controls where the watermark zone ends relative to text darkness.
                 0.2 = conservative (only remove obvious mid-gray),
                 0.5 = aggressive (also removes faint gray artifacts).
    Returns cleaned BGR image.
    """
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Estimate background brightness from the brightest pixels on the page
    bright = gray[gray > 200]
    if len(bright) < 500:
        return img_bgr  # Page too dark overall – skip
    bg_level = float(np.percentile(bright, 80))

    # Estimate text darkness from the darkest pixels
    dark = gray[gray < 150]
    if len(dark) < 200:
        return img_bgr  # No dark text found – skip
    text_level = float(np.percentile(dark, 20))

    # Watermark zone: between text darkness and background brightness
    zone_start = text_level + sensitivity * (bg_level - text_level)
    zone_end = bg_level - 8  # Stay below the actual white background

    if zone_end - zone_start < 15:
        return img_bgr  # Gap too narrow – document contrast too low

    mask = ((gray >= zone_start) & (gray <= zone_end)).astype(np.uint8)

    # Protect colored pixels: stamps (red), handwriting (blue/black ink often
    # has slight color bias).  A pixel is "colored" if one channel is
    # significantly stronger than the others.
    img_i = img_bgr.astype(np.int32)
    b, g, r = img_i[:, :, 0], img_i[:, :, 1], img_i[:, :, 2]
    max_channel_diff = np.maximum(
        np.maximum(np.abs(r - g), np.abs(r - b)), np.abs(g - b)
    )
    mask[max_channel_diff > 18] = 0

    # Skip if the mask is too small to be a real watermark
    if int(mask.sum()) < 300:
        return img_bgr

    result = img_bgr.copy()
    result[mask.astype(bool)] = [255, 255, 255]
    return result


def preprocess_pdf_for_ocr(pdf_path, dpi=None, sensitivity=None):
    """
    Create a watermark-removed copy of the PDF suitable for OCR.

    Returns the path to a cleaned temporary PDF file.
    If preprocessing is disabled or fails, returns the original pdf_path unchanged.
    The caller is responsible for deleting the returned temp file when finished
    (only when the returned path differs from pdf_path).
    """
    if not is_enabled():
        return pdf_path

    if dpi is None:
        try:
            dpi = int(os.environ.get("PREPROCESS_DPI", "300"))
        except ValueError:
            dpi = 250

    if sensitivity is None:
        try:
            sensitivity = float(os.environ.get("PREPROCESS_SENSITIVITY", "0.35"))
        except ValueError:
            sensitivity = 0.35

    try:
        import fitz
    except ImportError:
        return pdf_path

    try:
        src = fitz.open(pdf_path)
        dst = fitz.open()

        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)

        for idx in range(len(src)):
            page = src[idx]
            try:
                pix = page.get_pixmap(matrix=mat, alpha=False)
            except AttributeError:
                pix = page.getPixmap(matrix=mat, alpha=False)

            # fitz RGB → numpy BGR
            img_rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

            cleaned_bgr = remove_light_watermark(img_bgr, sensitivity=sensitivity)

            cleaned_rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
            clean_pix = fitz.Pixmap(
                fitz.csRGB, pix.width, pix.height, cleaned_rgb.tobytes()
            )

            # Preserve original page dimensions (points), embed raster image
            new_page = dst.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=clean_pix)

        src.close()

        tmp = tempfile.NamedTemporaryFile(
            suffix="_cleaned.pdf", delete=False, prefix="volc_pre_"
        )
        tmp.close()
        dst.save(tmp.name, deflate=True)
        dst.close()
        return tmp.name

    except Exception:
        return pdf_path


def visualize_removal(page_image_path, out_path=None, sensitivity=0.35):
    """
    Debug helper: side-by-side comparison of original vs cleaned page image.
    Saves to out_path or returns the combined numpy array.
    """
    img = cv2.imread(page_image_path)
    if img is None:
        raise FileNotFoundError(page_image_path)
    cleaned = remove_light_watermark(img, sensitivity=sensitivity)

    h = max(img.shape[0], cleaned.shape[0])
    divider = np.full((h, 4, 3), [200, 0, 0], dtype=np.uint8)
    combined = np.concatenate([img, divider, cleaned], axis=1)

    if out_path:
        cv2.imwrite(out_path, combined)
        return out_path
    return combined
