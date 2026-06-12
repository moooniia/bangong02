#!/usr/bin/env python3
import re
import zipfile

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"

with zipfile.ZipFile(WPS) as z:
    w = z.read("word/document.xml").decode("utf-8", errors="replace")
with zipfile.ZipFile(OURS) as z:
    o = z.read("word/document.xml").decode("utf-8", errors="replace")

wtext = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", w))
otext = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", o))

markers = [
    ("封面/合同号", "CMCCTD-SS-202400146"),
    ("服务合同", "服务合同"),
    ("签字页", "签字页"),
    ("签章页", "签章页"),
    ("工程概况", "1.工程概况"),
    ("基坑方案", "2.基坑围护方案简介"),
    ("监测表", "寄注"),
    ("供应商规则", "供应商负面行为"),
    ("大表60", "60IT硬件"),
    ("大表108", "108 电源"),
    ("第八条", "第八条本协议"),
]

print("=== MARKER PRESENCE ===")
for name, m in markers:
    print(f"{name:10s} WPS={m in wtext} OUR={m in otext}")

# WPS table cell samples
cells = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", w)
# find table regions
tbl_chunks = re.findall(r"<w:tbl[\s\S]*?</w:tbl>", w)
print(f"\nWPS tables={len(tbl_chunks)} OUR tables={o.count('<w:tbl')}")

for i, tbl in enumerate(tbl_chunks[:3], 1):
    tc = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tbl))
    print(f"\nWPS table{i} text_len={len(tc)} preview={tc[:120]}")

# signature page text in WPS
for kw in ["(签字页)", "签字/盖章", "合同专用章", "第八条"]:
    idx = wtext.find(kw)
    if idx >= 0:
        print(f"\nWPS around [{kw}]: {wtext[max(0,idx-30):idx+80]}")

for kw in ["(签字页)", "签字/盖章", "合同专用章", "第八条"]:
    idx = otext.find(kw)
    if idx >= 0:
        print(f"OUR around [{kw}]: {otext[max(0,idx-30):idx+80]}")
    else:
        print(f"OUR missing keyword: {kw}")

# image embedding in WPS - size distribution
extents = [(int(a), int(b)) for a,b in re.findall(r'cx="(\d+)"[^>]*cy="(\d+)"', w)]
print(f"\nWPS image count={len(extents)}")
bins = {"tiny<500k":0,"small<1.5M":0,"medium<3M":0,"large>=3M":0}
for cx,cy in extents:
    if cx < 500000: bins["tiny<500k"]+=1
    elif cx < 1500000: bins["small<1.5M"]+=1
    elif cx < 3000000: bins["medium<3M"]+=1
    else: bins["large>=3M"]+=1
print("WPS img bins", bins)

extents_o = [(int(a), int(b)) for a,b in re.findall(r'cx="(\d+)"[^>]*cy="(\d+)"', o)]
bins_o = {"tiny<500k":0,"small<1.5M":0,"medium<3M":0,"fullpage>=5M":0}
for cx,cy in extents_o:
    if cx < 500000: bins_o["tiny<500k"]+=1
    elif cx < 1500000: bins_o["small<1.5M"]+=1
    elif cx < 5000000: bins_o["medium<3M"]+=1
    else: bins_o["fullpage>=5M"]+=1
print("OUR img bins", bins_o)

print(f"\nWPS total text={len(wtext)} unique_chars={len(set(wtext))}")
print(f"OUR total text={len(otext)} unique_chars={len(set(otext))}")
print(f"WPS text not in OUR (sample): {(set(wtext)-set(otext)) and list(set(wtext)-set(otext))[:0]}")
# chars coverage
common = sum(1 for c in set(wtext) if c in otext)
print(f"char set overlap: WPS chars in OUR ratio ~ {len(set(wtext)&set(otext))}/{len(set(wtext))}")