import re
import zipfile
from collections import Counter

path = r"C:\Users\paz\Desktop\P T W 测试\A_site.docx"
with zipfile.ZipFile(path) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")

paras = re.findall(r"<w:p[^>]*>.*?</w:p>", doc, re.S)
print("paragraphs", len(paras))
styled = 0
for i, p in enumerate(paras[:20]):
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)
    if not texts:
        continue
    jc = re.search(r'w:jc w:val="(\w+)"', p)
    color = re.search(r'w:color w:val="([A-F0-9]+)"', p)
    bold = "<w:b/>" in p or 'w:b w:val="1"' in p
    sz = re.search(r'w:sz w:val="(\d+)"', p)
    ind = re.search(r'w:ind w:left="(\d+)"', p)
    if color or jc or ind:
        styled += 1
    print(
        f"p{i}: {''.join(texts)[:45]!r} align={jc.group(1) if jc else '-'} "
        f"color={color.group(1) if color else '-'} bold={bold} "
        f"sz={int(sz.group(1))/2 if sz else '-'} indent={ind.group(1) if ind else '-'}"
    )
print("styled_in_first20", styled)
print("anchors", doc.count("wp:anchor"), "tables", doc.count("<w:tbl>"))
print("colors", Counter(re.findall(r'w:color w:val="([A-F0-9]{6})"', doc)).most_common())