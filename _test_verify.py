import sys, traceback
sys.path.insert(0, "/home/toolbox/backend")
from volc_ocr import pdf_to_markdown_image_mode, pdf_page_count

pdf_path = "/tmp/A_test.pdf"
print(f"Testing A.pdf ({pdf_page_count(pdf_path)} pages)...")
try:
    pages_md = pdf_to_markdown_image_mode(pdf_path)
    print(f"SUCCESS: got {len(pages_md)} pages")
    for i, md in enumerate(pages_md):
        print(f"  page{i}: {len(md)} chars, preview={repr(md[:60])}")
except Exception as e:
    traceback.print_exc()
    print("FAILED:", e)
