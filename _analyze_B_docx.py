import re
import zipfile
from collections import Counter


def analyze(path, label):
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", "replace")
    shd = Counter(re.findall(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', doc))
    colors = Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
    print(f"=== {label} ===")
    print("shd fills", shd.most_common(10))
    print("text colors", colors.most_common(10))
    tbls = re.findall(r"<w:tbl>.*?</w:tbl>", doc, re.S)
    print("tables", len(tbls))
    paras = re.findall(r"<w:p[^>]*>.*?</w:p>", doc, re.S)
    for i, p in enumerate(paras[:12]):
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)
        if not texts:
            continue
        jc = re.search(r'w:jc w:val="(\w+)"', p)
        color = re.search(r'w:color w:val="([A-F0-9]+)"', p)
        bold = "w:b/" in p or 'w:b w:val="1"' in p or "<w:b/>" in p
        sz = re.search(r'w:sz w:val="(\d+)"', p)
        shd_fill = re.search(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', p)
        print(
            f"p{i}: {''.join(texts)[:50]!r} align={jc.group(1) if jc else None} "
            f"color={color.group(1) if color else None} bold={bold} "
            f"sz={int(sz.group(1))/2 if sz else None} shd={shd_fill.group(1) if shd_fill else None}"
        )
    if tbls:
        rows = re.findall(r"<w:tr>.*?</w:tr>", tbls[0], re.S)
        print(f"first table rows: {len(rows)}")
        for ri, row in enumerate(rows[:3]):
            cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
            for ci, cell in enumerate(cells[:4]):
                txt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", cell))
                shd_fill = re.search(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', cell)
                color = re.search(r'w:color w:val="([A-F0-9]+)"', cell)
                print(f"  r{ri}c{ci}: {txt[:30]!r} fill={shd_fill.group(1) if shd_fill else None} color={color.group(1) if color else None}")
    print()


analyze(r"C:\Users\paz\Desktop\B.docx", "WPS")
analyze(r"C:\Users\paz\Desktop\P T W 测试\B_site_styled.docx", "STYLED")