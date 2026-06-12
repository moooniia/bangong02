#!/usr/bin/env python3
from docx import Document
import zipfile

path = r"C:\Users\paz\Desktop\P T W 测试\page_1_p2_v096.docx"
doc = Document(path)
print("sections", len(doc.sections))
total_sb = 0.0
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    sb = p.paragraph_format.space_before
    sb_pt = sb.pt if sb else 0.0
    total_sb += sb_pt
    style = p.style.name if p.style else ""
    run = p.runs[0] if p.runs else None
    sz = run.font.size.pt if run and run.font.size else None
    bold = run.bold if run else None
    color = str(run.font.color.rgb) if run and run.font.color and run.font.color.rgb else None
    if t or sb_pt > 0:
        print(
            f"{i:02d} style={style!r} sb={sb_pt:.1f} sz={sz} bold={bold} color={color} | {t[:70]!r}"
        )
print("total_space_before", total_sb)
with zipfile.ZipFile(path) as z:
    xml = z.read("word/document.xml").decode("utf-8")
    print("page_breaks", xml.count("w:type=\"page\""))
    print("anchors", xml.count("wp:anchor"))
    print("inline", xml.count("wp:inline"))