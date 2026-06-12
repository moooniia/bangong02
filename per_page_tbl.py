import re, zipfile
doc = zipfile.ZipFile(r"C:\Users\paz\Desktop\1212_full.docx").read("word/document.xml").decode()
pages = doc.split('w:br w:type="page"')
for i, p in enumerate(pages[:12], 1):
    t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
    print(i, "tbl", p.count("<w:tbl"), "text", len(t))