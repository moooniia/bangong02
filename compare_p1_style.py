import re, zipfile

def p1_stats(path):
    doc = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", errors="replace")
    if "page" in path.lower() and "full" in path.lower():
        p1 = doc.split('w:br w:type="page"')[0]
    else:
        # WPS: first ~1200 chars of text as proxy for cover
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc)
        full = "".join(texts)
        idx = full.find("一、服务事项")
        p1 = doc[:doc.find("一、服务事项")] if idx > 0 else doc[:len(doc)//4]
    paras = []
    for p in re.findall(r"<w:p[ >][\s\S]*?</w:p>", p1):
        texts = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        if not texts and "<pic:pic" not in p:
            continue
        jc = re.search(r'w:jc w:val="(\w+)"', p)
        paras.append({
            "text": texts[:50],
            "align": jc.group(1) if jc else "left",
            "pics": p.count("<pic:pic"),
            "colors": re.findall(r'w:color w:val="([^"]+)"', p),
            "fonts": re.findall(r'w:eastAsia="([^"]+)"', p),
            "sz": re.findall(r'w:sz w:val="(\d+)"', p),
        })
    return paras

for name, path in [("WPS", r"C:\Users\paz\Desktop\1212.docx"), ("OUR", r"C:\Users\paz\Desktop\1212_full.docx")]:
    ps = p1_stats(path)
    print(f"\n=== {name} cover paras={len(ps)} ===")
    for i,p in enumerate(ps[:12],1):
        print(f"{i:2d} [{p['align']:6s}] pics={p['pics']} fonts={p['fonts'][:2]} sz={p['sz'][:2]} color={p['colors']} | {p['text']}")