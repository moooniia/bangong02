import os
import re
import zipfile
from collections import Counter

import requests

PDF = r"C:\Users\paz\Desktop\P T W 测试\A.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\A_site.docx"
URL = "http://139.196.28.78/api/convert"

with open(PDF, "rb") as f:
    r = requests.post(
        URL,
        files={"file": ("A.pdf", f, "application/pdf")},
        data={"format": "docx"},
        timeout=300,
    )

print("status", r.status_code)
data = r.json()
print("json", data)
if not data.get("success"):
    raise SystemExit(1)

dl = requests.get(f"http://139.196.28.78/api/download/{data['filename']}", timeout=120)
dl.raise_for_status()
with open(OUT, "wb") as f:
    f.write(dl.content)
print("saved", OUT, "bytes", len(dl.content))

with zipfile.ZipFile(OUT) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")
colors = Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
fills = Counter(re.findall(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', doc))
text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
print("route", data.get("route"), "warning", data.get("warning", ""))
print("colors", colors.most_common(8))
print("fills", fills.most_common(8))
print("tables", doc.count("<w:tbl"), "chars", len(text))
print("preview", text[:400].replace("\n", " "))