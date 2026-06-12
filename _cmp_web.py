import re
import zipfile
from collections import Counter

paths = {
    "WEB": r"C:\Users\paz\Desktop\P T W 测试\B_web.docx",
    "STYLED": r"C:\Users\paz\Desktop\P T W 测试\B_site_styled.docx",
}
for label, path in paths.items():
    doc = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
    colors = Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc))
    fills = Counter(re.findall(r'w:shd[^>]*w:fill="([A-F0-9]{6})"', doc))
    print(label, "colors", colors.most_common(5), "fills", fills.most_common(3), "tables", doc.count("<w:tbl>"))