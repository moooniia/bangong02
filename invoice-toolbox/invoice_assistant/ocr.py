import platform
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]
SWIFT_SOURCE = ROOT / "tools" / "vision_ocr.swift"
OCR_BINARY = ROOT / "tools" / "vision_ocr_bin"
_OCR_LOCAL = threading.local()


@dataclass
class OcrLine:
    text: str
    x: float
    y: float
    width: float
    height: float


def recognize_image(path: Path) -> List[OcrLine]:
    rapid_result = _recognize_with_rapidocr(path)
    if rapid_result:
        return rapid_result
    if platform.system() != "Darwin":
        raise RuntimeError("RapidOCR 未能识别该文件")
    return _recognize_with_vision(path)


def _recognize_with_rapidocr(path: Path) -> List[OcrLine]:
    try:
        from PIL import Image
        import fitz
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return []

    engine = getattr(_OCR_LOCAL, "engine", None)
    if engine is None:
        engine = RapidOCR()
        _OCR_LOCAL.engine = engine

    lines = []
    try:
        if path.suffix.lower() == ".pdf":
            document = fitz.open(str(path))
            try:
                text_layer = _extract_pdf_text_layer(document)
                if text_layer:
                    return text_layer
                for page in list(document)[:1]:
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                        pixmap.height, pixmap.width, pixmap.n
                    )
                    result, _ = engine(image)
                    page_lines = _lines_from_result(result, pixmap.width, pixmap.height)
                    lines.extend(page_lines)
                    if _needs_party_crops(page_lines):
                        lines.extend(_recognize_party_crops(engine, image))
            finally:
                document.close()
        else:
            image = Image.open(path)
            width, height = image.size
            result, _ = engine(str(path))
            image_lines = _lines_from_result(result, width, height)
            lines.extend(image_lines)
            if _needs_party_crops(image_lines):
                lines.extend(_recognize_party_crops(engine, np.asarray(image.convert("RGB"))))
    except Exception:
        return []
    return lines


def _extract_pdf_text_layer(document) -> List[OcrLine]:
    lines: List[OcrLine] = []
    total_text = 0
    for page in list(document)[:1]:
        page_width = float(page.rect.width or 1)
        page_height = float(page.rect.height or 1)
        # PDF blocks can merge the buyer and seller columns in an arbitrary
        # text order. Atomic word coordinates preserve their visual columns.
        for word in page.get_text("words"):
            if len(word) < 5:
                continue
            x0, y0, x1, y1, text = word[:5]
            text = str(text).strip()
            if not text:
                continue
            lines.append(
                OcrLine(
                    text=text,
                    x=float(x0) / page_width,
                    y=1 - (float(y1) / page_height),
                    width=max(0.0, float(x1 - x0) / page_width),
                    height=max(0.0, float(y1 - y0) / page_height),
                )
            )
        for block in page.get_text("blocks"):
            if len(block) < 5:
                continue
            x0, y0, x1, y1, text = block[:5]
            text = " ".join(str(text).split())
            if not text:
                continue
            total_text += len(text)
            lines.append(
                OcrLine(
                    text=text,
                    x=float(x0) / page_width,
                    y=1 - (float(y1) / page_height),
                    width=max(0.0, float(x1 - x0) / page_width),
                    height=max(0.0, float(y1 - y0) / page_height),
                )
            )
    joined = "".join(line.text for line in lines)
    control_count = sum(ord(char) < 32 and not char.isspace() for char in joined)
    meaningful_count = sum(char.isalnum() or "\u4e00" <= char <= "\u9fff" for char in joined)
    meaningful_ratio = meaningful_count / max(1, len(joined))
    if total_text < 100 or len(lines) < 8 or control_count > 0 or meaningful_ratio < 0.35:
        return []
    return lines


def _lines_from_result(result, width: int, height: int) -> List[OcrLine]:
    lines = []
    for item in result or []:
        if len(item) < 3:
            continue
        box, text, _score = item
        text = text.strip()
        if text:
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            min_x = min(xs) / width
            min_y = 1 - (max(ys) / height)
            box_width = (max(xs) - min(xs)) / width
            box_height = (max(ys) - min(ys)) / height
            lines.append(OcrLine(text=text, x=min_x, y=min_y, width=box_width, height=box_height))
    return lines


def _needs_party_crops(lines: List[OcrLine]) -> bool:
    party_lines = [line for line in lines if 0.50 <= line.y <= 0.82]
    tokens = ("公司", "研究院", "分院", "中心", "银行", "学校", "商行", "店", "厂")
    has_left = any(line.x + line.width <= 0.52 and any(token in line.text for token in tokens) for line in party_lines)
    has_right = any(line.x >= 0.48 and any(token in line.text for token in tokens) for line in party_lines)
    return not (has_left and has_right)


def _recognize_party_crops(engine, image) -> List[OcrLine]:
    height, width = image.shape[:2]
    y0, y1 = int(height * 0.15), int(height * 0.50)
    lines: List[OcrLine] = []
    for x0, x1 in ((0, int(width * 0.50)), (int(width * 0.50), width)):
        crop = image[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        result, _ = engine(crop)
        for item in result or []:
            if len(item) < 3:
                continue
            box, text, _score = item
            text = text.strip()
            if not text:
                continue
            xs = [point[0] + x0 for point in box]
            ys = [point[1] + y0 for point in box]
            lines.append(
                OcrLine(
                    text=text,
                    x=min(xs) / width,
                    y=1 - (max(ys) / height),
                    width=(max(xs) - min(xs)) / width,
                    height=(max(ys) - min(ys)) / height,
                )
            )
    return lines


def _recognize_with_vision(path: Path) -> List[OcrLine]:
    _ensure_binary()
    proc = subprocess.run(
        [str(OCR_BINARY), str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"OCR failed for {path}")
    lines = []
    for raw in proc.stdout.splitlines():
        parts = raw.split("\t", 4)
        if len(parts) != 5:
            continue
        x, y, width, height, text = parts
        text = text.strip()
        if text:
            lines.append(OcrLine(text=text, x=float(x), y=float(y), width=float(width), height=float(height)))
    return lines


def _ensure_binary() -> None:
    if OCR_BINARY.exists() and OCR_BINARY.stat().st_mtime >= SWIFT_SOURCE.stat().st_mtime:
        return
    subprocess.run(
        ["swiftc", str(SWIFT_SOURCE), "-o", str(OCR_BINARY)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
