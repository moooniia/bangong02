import re
import zipfile

import fitz
import requests

CASES = [
    ("A", r"C:\Users\paz\Desktop\P T W 测试\A.pdf", "volc-hybrid"),
    ("B", r"C:\Users\paz\Desktop\P T W 测试\B.pdf", "volc-image-table"),
    ("C", r"C:\Users\paz\Desktop\P T W 测试\C.pdf", "volc-normal"),
]
URL = "http://139.196.28.78/api/convert"


def page_breaks(doc_xml):
    return doc_xml.count("w:br") + doc_xml.count('w:type="page"')


def analyze(label, pdf_path, expect_route, out_path):
    with open(pdf_path, "rb") as f:
        r = requests.post(
            URL,
            files={"file": (label + ".pdf", f, "application/pdf")},
            data={"format": "docx"},
            timeout=600,
        )
    data = r.json()
    print(f"\n=== {label} ===")
    print("api", data)
    assert data.get("success"), data
    if expect_route:
        assert data.get("route") == expect_route, data

    dl = requests.get(f"{URL.replace('/api/convert', '')}/api/download/{data['filename']}", timeout=120)
    with open(out_path, "wb") as f:
        f.write(dl.content)

    pdf_pages = fitz.open(pdf_path).page_count
    with zipfile.ZipFile(out_path) as z:
        doc = z.read("word/document.xml").decode("utf-8", "replace")
    breaks = page_breaks(doc)
    doc_pages = breaks + 1
    colors = set(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
    fills = set(re.findall(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', doc))
    tables = doc.count("<w:tbl>")
    anchors = doc.count("wp:anchor")
    text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
    pics = doc.count("<w:drawing>")
    print(f"pdf={pdf_pages} doc_pages≈{doc_pages} tables={tables} anchors={anchors} pics={pics}")
    print(f"colors={sorted(colors)} fills={sorted(fills)} chars={len(text)} bytes={len(dl.content)}")
    print(f"warning={data.get('warning') or '-'}")
    if label == "A":
        assert doc_pages >= pdf_pages, f"A missing pages: pdf {pdf_pages} doc {doc_pages}"
        assert anchors >= 1 or pics >= 1, "A should keep seals/images"
    if label == "B":
        assert "1E4D78" in fills or "C60000" in colors, "B styling lost"
    return data


for label, path, route in CASES:
    out = rf"C:\Users\paz\Desktop\P T W 测试\{label}_p0.docx"
    analyze(label, path, route, out)
print("\nALL OK")