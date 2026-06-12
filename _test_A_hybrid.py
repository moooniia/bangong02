import re
import zipfile

import requests

PDF = r"C:\Users\paz\Desktop\P T W 测试\A.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\A_site.docx"

with open(PDF, "rb") as f:
    r = requests.post(
        "http://139.196.28.78/api/convert",
        files={"file": ("A.pdf", f, "application/pdf")},
        data={"format": "docx"},
        timeout=600,
    )
data = r.json()
print("response", data)
assert data.get("success"), data

dl = requests.get(f"http://139.196.28.78/api/download/{data['filename']}", timeout=120)
with open(OUT, "wb") as f:
    f.write(dl.content)
print("saved", OUT, len(dl.content))

with zipfile.ZipFile(OUT) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")
    rels = z.read("word/_rels/document.xml.rels").decode("utf-8", "replace")
text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
colors = set(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
fills = set(re.findall(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', doc))
images = rels.count("image")
anchors = doc.count("wp:anchor")
tables = doc.count("<w:tbl>")
print("route", data.get("route"))
print("chars", len(text), "tables", tables, "colors", sorted(colors), "fills", sorted(fills))
print("images", images, "floating", anchors)
print("preview", text[:350])