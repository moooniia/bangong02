import re
import zipfile

doc = zipfile.ZipFile(r"C:\Users\paz\Desktop\1212_full.docx").read("word/document.xml").decode("utf-8", "replace")
pages = doc.split('w:br w:type="page"')
all_text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
for i, p in enumerate(pages[:12], 1):
    t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
    print(f"p{i}: len={len(t)} pics={p.count('<pic:pic')} | {t[:70]}")
print("wm_frag", any(w in all_text for w in ("臻子", "至善", "德厚", "李于", "正德")))