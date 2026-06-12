"""Visual test: watermark removal on 1212 page images."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

from preprocessing import visualize_removal

PAGE_DIR = r"C:\Users\paz\Desktop\1212\pdf_pages"
OUT_DIR = r"C:\Users\paz\Desktop\1212\preprocessed"
os.makedirs(OUT_DIR, exist_ok=True)

# Test on the pages most affected by watermarks
TEST_PAGES = ["page_001.png", "page_003.png", "page_006.png", "page_005.png"]

for fname in TEST_PAGES:
    src = os.path.join(PAGE_DIR, fname)
    out = os.path.join(OUT_DIR, fname.replace(".png", "_compare.jpg"))
    visualize_removal(src, out_path=out, sensitivity=0.35)
    size_kb = os.path.getsize(out) // 1024
    print(f"  {fname} → {out}  ({size_kb} KB)")

print(f"\nOpen {OUT_DIR} to see before/after comparisons (left=original, right=cleaned).")
