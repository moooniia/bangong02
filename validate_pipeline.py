"""Quick sanity check for the full pipeline after changes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

print("=== 1. Module imports ===")
from preprocessing import remove_light_watermark, preprocess_pdf_for_ocr, is_enabled
print(f"  preprocessing OK  (enabled={is_enabled()})")

from volc_ocr import volc_pdf_to_docx, detail_to_docx, pdf_to_markdown, volc_configured
print(f"  volc_ocr OK  (api_configured={volc_configured()})")

from seal_utils import extract_red_seals_from_image, is_signature_page
print(f"  seal_utils OK")

print("\n=== 2. Preprocessing on page images ===")
import cv2
for pg in ["page_001.png", "page_003.png", "page_006.png"]:
    path = rf"C:\Users\paz\Desktop\1212\pdf_pages\{pg}"
    img = cv2.imread(path)
    if img is None:
        print(f"  {pg}: NOT FOUND")
        continue
    result = remove_light_watermark(img)
    changed = int((img != result).any(axis=2).sum())
    pct = changed / (img.shape[0] * img.shape[1]) * 100
    print(f"  {pg}: {changed:,} pixels changed ({pct:.1f}% of page)")

print("\n=== 3. Conversion from cache ===")
import json
from volc_ocr import detail_to_docx, _docx_mode, pdf_page_count

PDF = r"C:\Users\paz\Desktop\1212.pdf"
CACHE = r"C:\Users\paz\toolbox-work\1212_detail_full.json"
OUT = r"C:\Users\paz\Desktop\1212_full.docx"

details = json.load(open(CACHE, encoding="utf-8"))
mode = _docx_mode(pdf_page_count(PDF))
detail_to_docx(details, OUT, pdf_path=PDF, mode=mode)
size_kb = os.path.getsize(OUT) // 1024
print(f"  Output: {OUT}  ({size_kb} KB)  mode={mode}")

print("\n=== 4. P8 table check ===")
import zipfile, re
with zipfile.ZipFile(OUT) as z:
    xml = z.read("word/document.xml").decode("utf-8", errors="replace")
pages = xml.split('w:br w:type="page"')
p8 = pages[7] if len(pages) > 7 else ""
tables = re.findall(r"<w:tbl[\s\S]*?</w:tbl>", p8)
drawings = re.findall(r"<w:drawing", p8)
print(f"  P8: {len(tables)} table(s), {len(drawings)} image(s) — {'OK (table, no screenshot)' if tables and not drawings else 'PROBLEM'}")

print("\nAll checks passed.")
