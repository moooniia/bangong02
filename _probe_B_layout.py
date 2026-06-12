import sys, os, re, zipfile, json, base64
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import run

# Volc HTML sample
cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import base64, fitz, re
import sys; sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import _visual_service, _ocr_pdf_image_page, _page_rgb_and_b64
visual = _visual_service()
b64,_ = _page_rgb_and_b64("/tmp/B.pdf", 0)
md = _ocr_pdf_image_page(visual, b64)
tables = re.findall(r"<table[\s\S]*?</table>", md, re.I)
print("tables_in_md", len(tables))
if tables:
    t = tables[0]
    print("has_style", "style=" in t.lower(), "bgcolor", "bgcolor" in t.lower(), "color", "color" in t.lower())
    print("has_colspan", "colspan" in t.lower(), "has_rowspan", "rowspan" in t.lower())
    print("snippet", t[:500])
PYEOF
"""
_, out, err = run(cmd, timeout=120)
print("=== Volc HTML ===")
print(out or err)

def docx_layout(path, label):
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", "replace")
    colors = Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
    fills = Counter(re.findall(r'w:fill w:val="([A-F0-9]{6})"', doc))
    sizes = sorted(set(int(s)/2 for s in re.findall(r'w:sz w:val="(\d+)"', doc)))
    tbl_grid = doc.count("w:tblGrid")
    print(f"=== {label} ===")
    print("colors", colors.most_common(8))
    print("cell_fills", fills.most_common(8))
    print("sizes_pt", sizes[:12])
    print("tblGrid", tbl_grid, "tables", doc.count("<w:tbl"))
    print()

docx_layout(r"C:\Users\paz\Desktop\P T W 测试\B_site.docx", "我们")
docx_layout(r"C:\Users\paz\Desktop\B.docx", "WPS")