import json

d300 = json.load(open("1212_detail_300dpi.json", encoding="utf-8"))
d250 = json.load(open("1212_detail_fresh.json", encoding="utf-8"))
dold = json.load(open("1212_detail_full.json", encoding="utf-8"))

print("Page | old(no-pre) | 250dpi | 300dpi | change")
print("-" * 60)
for i in range(12):
    def info(pages, idx):
        p = pages[idx]
        blk = p.get("textblocks", [])
        chars = sum(len((b.get("text") or "").strip()) for b in blk if (b.get("label") or "") != "foot")
        tbl = any("<table" in (b.get("text") or "").lower() for b in blk)
        return chars, tbl

    oc, ot = info(dold, i)
    nc, nt = info(d250, i)
    rc, rt = info(d300, i)

    def fmt(c, t):
        return f"{c:5d}{'T' if t else '-'}"

    note = ""
    if rt and not ot: note = " p04-table-new"
    if rt and not nt: note = " p11-RECOVERED"
    if nt and not rt: note = " TABLE-LOST"
    print(f" p{i+1:02d} | {fmt(oc,ot)} | {fmt(nc,nt)} | {fmt(rc,rt)} |{note}")
