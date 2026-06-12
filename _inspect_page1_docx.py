#!/usr/bin/env python3
from docx import Document
import zipfile

path = r"C:\Users\paz\Desktop\P T W 测试\page_1_p2_v093.docx"
doc = Document(path)
print("sections", len(doc.sections))
for si, sec in enumerate(doc.sections):
    print(
        f"section {si}: h={sec.page_height} w={sec.page_width} "
        f"top={sec.top_margin} bottom={sec.bottom_margin}"
    )

total_sb = 0.0
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    sb = p.paragraph_format.space_before
    sa = p.paragraph_format.space_after
    sb_pt = sb.pt if sb else 0.0
    sa_pt = sa.pt if sa else 0.0
    total_sb += sb_pt
    style = p.style.name if p.style else ""
    sz = p.runs[0].font.size.pt if p.runs and p.runs[0].font.size else None
    has_pic = any("graphic" in r._element.xml for r in p.runs) if p.runs else False
    print(
        f"{i:02d} style={style!r} sb={sb_pt:.1f} sa={sa_pt:.1f} sz={sz} pic={has_pic} | {t[:70]!r}"
    )
print("total_space_before", total_sb)

with zipfile.ZipFile(path) as z:
    xml = z.read("word/document.xml").decode("utf-8")
    print("page_breaks", xml.count("w:type=\"page\""))
    print("drawings", xml.count("wp:inline"))