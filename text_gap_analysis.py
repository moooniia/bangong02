import re, zipfile

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"

def text(p):
    doc = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", errors="replace")
    return re.sub(r"\s+", "", "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc)))

w, o = text(WPS), text(OURS)
print("wps_len", len(w), "our_len", len(o), "ratio", round(len(o)/len(w),3))

# find phrases in WPS missing in ours (sample)
import json
phrases = [
    "签字页", "签章页", "签字/盖章", "第八条", "第九条", "合同专用章",
    "授权代表", "法定代表人", "工程概况", "基坑围护", "供应商负面",
    "108", "电源及动力", "60IT", "运维楼", "青浦",
]
for p in phrases:
    print(f"{p}: wps={p in w} our={p in o}")

# char diff magnitude
common = sum(1 for i in range(0, min(len(w), len(o)), 50) if w[i:i+50] in o)
print("rough_overlap_blocks", common)