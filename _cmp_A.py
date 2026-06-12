import zipfile

for label, path in [
    ("SITE", r"C:\Users\paz\Desktop\P T W 测试\A_site.docx"),
    ("IMAGE", r"C:\Users\paz\Desktop\P T W 测试\A_image.docx"),
]:
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", "replace")
    text = "".join(__import__("re").findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
    print(label, "bytes", __import__("os").path.getsize(path), "tables", doc.count("<w:tbl>"), "chars", len(text))
    print("  start:", text[:200])
    print()