import sys
from pathlib import Path

from PIL import Image
from rapidocr_onnxruntime import RapidOCR


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: rapid_ocr.py <image>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    image = Image.open(path)
    width, height = image.size
    ocr = RapidOCR()
    result, _ = ocr(str(path))
    for item in result or []:
        box, text, score = item
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        min_x = min(xs) / width
        min_y = 1 - (max(ys) / height)
        box_width = (max(xs) - min(xs)) / width
        box_height = (max(ys) - min(ys)) / height
        print(f"{min_x}\t{min_y}\t{box_width}\t{box_height}\t{score}\t{text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

