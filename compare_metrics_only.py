import os, re, zipfile

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"

def m(p):
    doc = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", errors="replace")
    t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
    ex = [int(x) for x in re.findall(r'cx="(\d+)"', doc)]
    kw = {k: k in t for k in ("签字页","签章页","签字/盖章","第八条","60IT硬件","108","电源及动力")}
    return {
        "text": len(t), "tables": doc.count("<w:tbl"), "fullpage": sum(1 for x in ex if x > 5_000_000),
        "pics": doc.count("<pic:pic"), "mb": round(os.path.getsize(p)/1048576, 2), "kw": kw,
    }

w, o = m(WPS), m(OURS)
print("WPS", w)
print("OUR", o)
print("text_ratio", round(o["text"]/w["text"], 3))