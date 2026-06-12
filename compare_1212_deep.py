#!/usr/bin/env python3
import os
import re
import zipfile
from collections import Counter

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"


def read_doc(path):
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", errors="replace")
        media = {n: z.getinfo(n).file_size for n in z.namelist() if n.startswith("word/media/")}
    return doc, media


def image_extents(doc):
    pairs = re.findall(r'cx="(\d+)"[^>]*cy="(\d+)"', doc)
    items = [(int(a), int(b)) for a, b in pairs]
    return items


def split_ours_pages(doc):
    return doc.split('w:br w:type="page"')


def split_wps_logical(doc):
    """WPS 无分页符时，用合同编号/签章页等锚点粗分逻辑页"""
    anchors = [
        "CMCCTD-SS-202400146",
        "(签字页)",
        "(签章页)",
        "1.工程概况",
        "2.基坑围护方案简介",
        "供应商负面行为处理规则",
        "60IT硬件",
        "108 电源",
        "第八条本协议",
    ]
    texts_with_pos = []
    for m in re.finditer(r"<w:t[^>]*>([^<]*)</w:t>", doc):
        texts_with_pos.append((m.start(), m.group(1)))
    full = "".join(t for _, t in texts_with_pos)
    sections = []
    positions = [0]
    for a in anchors[1:]:
        idx = full.find(a)
        if idx > 0:
            positions.append(idx)
    positions = sorted(set(positions))
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(full)
        sections.append(full[start:end])
    return sections if len(sections) >= 6 else [full]


def page_metrics(blob):
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", blob) if "<w:t" in blob else [blob]
    text = "".join(texts) if "<w:t" in blob else blob
    tables = blob.count("<w:tbl") if "<w:t" not in blob else 0
    pics = blob.count("<pic:pic") if "<w:t" not in blob else 0
    extents = [int(x) for x in re.findall(r'cx="(\d+)"', blob)]
    max_cx = max(extents) if extents else 0
    return {
        "text_len": len(text.strip()),
        "tables": tables,
        "pics": pics,
        "max_img_cx": max_cx,
        "fullpage_img": max_cx > 5_000_000,
        "preview": text.strip()[:90],
    }


def font_color_stats(doc):
    fonts = Counter(re.findall(r'w:eastAsia="([^"]+)"', doc))
    colors = Counter(re.findall(r'w:color w:val="([^"]+)"', doc))
    return fonts.most_common(6), colors.most_common(6)


def main():
    wdoc, wmedia = read_doc(WPS)
    odoc, omedia = read_doc(OURS)

    w_ext = image_extents(wdoc)
    o_ext = image_extents(odoc)

    print("=== FILE ===")
    print(f"WPS  size={os.path.getsize(WPS)/1024/1024:.2f}MB media={len(wmedia)} total_media_kb={sum(wmedia.values())//1024}")
    print(f"OURS size={os.path.getsize(OURS)/1024/1024:.2f}MB media={len(omedia)} total_media_kb={sum(omedia.values())//1024}")

    print("\n=== IMAGE STRATEGY ===")
    for name, ext in ("WPS", w_ext), ("OURS", o_ext):
        if not ext:
            print(name, "no images")
            continue
        fullpage = sum(1 for cx, cy in ext if cx > 5_000_000)
        small = sum(1 for cx, cy in ext if cx <= 2_000_000)
        print(f"{name}: images={len(ext)} fullpage(>5M cx)={fullpage} small(<=2M)={small} max_cx={max(cx for cx,_ in ext)}")

    print("\n=== STRUCTURE ===")
    print(f"WPS: page_breaks={wdoc.count('w:br w:type=\"page\"')} tables={wdoc.count('<w:tbl')} paras={wdoc.count('<w:p ')}")
    print(f"OURS: page_breaks={odoc.count('w:br w:type=\"page\"')} tables={odoc.count('<w:tbl')} paras={odoc.count('<w:p ')}")

    wf, wc = font_color_stats(wdoc)
    of, oc = font_color_stats(odoc)
    print("\n=== FONTS ===")
    print("WPS ", wf)
    print("OURS", of)
    print("=== COLORS ===")
    print("WPS ", wc)
    print("OURS", oc)

    wsec = split_wps_logical(wdoc)
    osec = split_ours_pages(odoc)
    print(f"\n=== LOGICAL SECTIONS: WPS={len(wsec)} OURS={len(osec)} ===")
    n = max(len(wsec), len(osec))
    for i in range(n):
        wm = page_metrics(wsec[i]) if i < len(wsec) else {}
        om = page_metrics(osec[i]) if i < len(osec) else {}
        print(f"\n--- section {i+1} ---")
        print(f"  WPS : text={wm.get('text_len',0)} tbl={wm.get('tables',0)} pics={wm.get('pics',0)} fullpage={wm.get('fullpage_img',False)}")
        print(f"  OURS: text={om.get('text_len',0)} tbl={om.get('tables',0)} pics={om.get('pics',0)} fullpage={om.get('fullpage_img',False)}")
        if wm.get("preview"):
            print(f"  WPS preview : {wm['preview']}")
        if om.get("preview"):
            print(f"  OUR preview: {om['preview']}")

    # 签章/表格页判定
    print("\n=== PAGE TYPE READOUT ===")
    labels = [
        "封面", "合同正文", "签字页", "规格书1", "规格书2",
        "签章页1", "签章页2", "监测表", "供应商规则", "横页大表1", "横页大表2", "签章尾页",
    ]
    for i in range(min(12, len(osec))):
        om = page_metrics(osec[i])
        wm = page_metrics(wsec[i]) if i < len(wsec) else {"text_len": 0, "fullpage_img": False, "tables": 0}
        label = labels[i] if i < len(labels) else f"p{i+1}"
        if om["fullpage_img"] and om["text_len"] < 50:
            our_note = "整页截图为主"
        elif om["text_len"] > 200 and not om["fullpage_img"]:
            our_note = "可编辑文字为主"
        else:
            our_note = "混合"
        if wm.get("text_len", 0) > 200:
            wps_note = "可编辑文字"
        elif wm.get("tables", 0) > 0:
            wps_note = "表格结构"
        else:
            wps_note = "图文混合"
        winner = "WPS" if wm.get("text_len", 0) > om["text_len"] + 100 else ("我们" if om["text_len"] > wm.get("text_len", 0) + 100 and not om["fullpage_img"] else "接近")
        print(f"{i+1:2d} {label:8s} | WPS:{wps_note:10s} OUR:{our_note:12s} | 文字 WPS={wm.get('text_len',0):4d} OUR={om['text_len']:4d} | {winner}")


if __name__ == "__main__":
    main()