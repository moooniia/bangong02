import re
import zipfile

with zipfile.ZipFile(r"C:\Users\paz\Desktop\B.docx") as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")

tbls = re.findall(r"<w:tbl>.*?</w:tbl>", doc, re.S)
for ti, tbl in enumerate(tbls):
    rows = re.findall(r"<w:tr>.*?</w:tr>", tbl, re.S)
    for ri, row in enumerate(rows):
        cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
        for ci, cell in enumerate(cells):
            shd = re.search(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', cell)
            if shd and shd.group(1) == "FEF2DF":
                txt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", cell))
                print(f"t{ti} r{ri} c{ci}: {txt[:50]!r}")