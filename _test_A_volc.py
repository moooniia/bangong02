import os
import re
import sys
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import fetch, put, run

PDF = r"C:\Users\paz\Desktop\P T W 测试\A.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\A_volc.docx"
put(PDF, "/tmp/A.pdf")

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx
info = volc_pdf_to_docx("/tmp/A.pdf", "/tmp/A_volc.docx")
print(info)
PYEOF
"""
_, out, err = run(cmd, timeout=300)
print(out or err)
fetch("/tmp/A_volc.docx", OUT)

with zipfile.ZipFile(OUT) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")
colors = Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
fills = Counter(re.findall(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', doc))
text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
print("colors", colors.most_common(8))
print("fills", fills.most_common(8))
print("tables", doc.count("<w:tbl"), "chars", len(text))
print("preview", text[:500])