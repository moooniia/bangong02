import zipfile, re
with zipfile.ZipFile(r"C:\Users\paz\Desktop\1212_full.docx") as z:
    xml = z.read("word/document.xml").decode("utf-8", errors="replace")

pages = xml.split('w:br w:type="page"')
print(f"Total pages: {len(pages)}")
p8 = pages[7]
tables = re.findall(r"<w:tbl[\s\S]*?</w:tbl>", p8)
texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p8)
drawings = re.findall(r"<w:drawing", p8)
print(f"P8: tables={len(tables)}, text_runs={len(texts)}, drawings={len(drawings)}")
if tables:
    sample = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tables[0]))[:150]
    print(f"  Table content: {repr(sample)}")
print(f"  All text: {repr(''.join(texts)[:200])}")
