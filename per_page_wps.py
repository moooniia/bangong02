import re, zipfile
doc = zipfile.ZipFile(r"C:\Users\paz\Desktop\1212.docx").read("word/document.xml").decode()
# WPS no page breaks - count tables between text anchors
text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
print("total tbl", doc.count("<w:tbl"), "text", len(text))
# split by table positions
parts = re.split(r"(<w:tbl[\s\S]*?</w:tbl>)", doc)
print("table chunks", sum(1 for p in parts if p.startswith("<w:tbl")))