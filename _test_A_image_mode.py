import os
import re
import sys
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import fetch, run

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import pdf_to_markdown_image_mode, markdown_pages_to_docx, _markdown_has_usable_content
pages = pdf_to_markdown_image_mode("/tmp/A.pdf")
combined = "\n\n".join(p for p in pages if p)
print("pages", len(pages), "usable", _markdown_has_usable_content(combined), "total_len", len(combined))
print("tables", combined.lower().count("<table"))
markdown_pages_to_docx(pages, "/tmp/A_image.docx")
print("saved")
PYEOF
"""
_, out, err = run(cmd, timeout=300)
print(out or err)
fetch("/tmp/A_image.docx", r"C:\Users\paz\Desktop\P T W 测试\A_image.docx")

with zipfile.ZipFile(r"C:\Users\paz\Desktop\P T W 测试\A_image.docx") as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")
colors = Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
print("colors", colors.most_common(5))
print("tables", doc.count("<w:tbl"), "chars", len(text))
print("preview", text[:600])