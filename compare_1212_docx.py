#!/usr/bin/env python3
"""对比 WPS 版与自研版 1212.docx"""
import re
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def analyze(path):
    with zipfile.ZipFile(path) as z:
        doc_xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8", errors="replace")
        styles = z.read("word/styles.xml").decode("utf-8", errors="replace") if "word/styles.xml" in z.namelist() else ""

    pages = doc_xml.split('w:br w:type="page"')
    if len(pages) < 2:
        pages = [doc_xml]

    page_stats = []
    for i, px in enumerate(pages, 1):
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", px)
        text = "".join(texts)
        pics = px.count("<pic:pic")
        drawings = px.count("<w:drawing")
        tables = px.count("<w:tbl")
        big_img = bool(re.search(r'cx="([0-9]+)"', px) and max(int(m) for m in re.findall(r'cx="([0-9]+)"', px) or ["0"]) > 5_000_000)
        fonts = Counter()
        colors = Counter()
        align = Counter()
        for p in re.findall(r"<w:p[ >][\s\S]*?</w:p>", px):
            jc = re.search(r'w:jc w:val="(\w+)"', p)
            if jc:
                align[jc.group(1)] += 1
            for r in re.findall(r"<w:r[\s\S]*?</w:r>", p):
                t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r))
                if not t:
                    continue
                font = re.search(r'w:eastAsia="([^"]+)"', r) or re.search(r'w:ascii="([^"]+)"', r)
                if font:
                    fonts[font.group(1)] += 1
                color = re.search(r'w:color w:val="([^"]+)"', r)
                if color:
                    colors[color.group(1)] += 1
        page_stats.append({
            "page": i,
            "text_len": len(text.strip()),
            "pics": pics,
            "drawings": drawings,
            "tables": tables,
            "big_img": big_img,
            "fonts": dict(fonts.most_common(5)),
            "colors": dict(colors.most_common(5)),
            "align": dict(align),
            "preview": text.strip()[:100],
        })

    all_text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc_xml))
    wm_hits = [w for w in ("臻子", "至善", "德厚", "李于", "正德", "厚生") if w in all_text]

    # 估算整页图占比：超大 extent 的图片
    extents = [int(x) for x in re.findall(r'cx="([0-9]+)"', doc_xml)]
    huge_extents = sum(1 for x in extents if x > 5_000_000)

    return {
        "path": path,
        "size_mb": round(zipfile.ZipFile(path).namelist().__len__() and __import__("os").path.getsize(path) / 1048576, 2),
        "media_count": len(media),
        "page_sections": len(pages),
        "total_text_len": len(all_text.strip()),
        "paragraphs": doc_xml.count("<w:p "),
        "tables": doc_xml.count("<w:tbl"),
        "pics": doc_xml.count("<pic:pic"),
        "drawings": doc_xml.count("<w:drawing"),
        "huge_images": huge_extents,
        "wm_hits": wm_hits,
        "editable_ratio": round(len(all_text.strip()) / max(len(all_text.strip()) + doc_xml.count("<pic:pic") * 500, 1), 3),
        "pages": page_stats,
        "has_blue_stamp": "008FEF" in doc_xml or "008fef" in doc_xml.lower(),
        "font_sample": Counter(re.findall(r'w:eastAsia="([^"]+)"', doc_xml)).most_common(8),
    }


def verdict(wps, ours):
    lines = []
    # 逐页对比
    for wp, op in zip(wps["pages"], ours["pages"]):
        p = wp["page"]
        if wp["text_len"] > 80 and op["text_len"] < 30 and op["big_img"]:
            lines.append(f"p{p}: 我们整页截图，WPS有可编辑文字({wp['text_len']}字)")
        elif wp["text_len"] < 30 and op["text_len"] > 80:
            lines.append(f"p{p}: 我们文字更好({op['text_len']}字)，WPS几乎无字")
        elif abs(wp["text_len"] - op["text_len"]) > 300:
            longer = "WPS" if wp["text_len"] > op["text_len"] else "我们"
            lines.append(f"p{p}: {longer}文字更多 (WPS {wp['text_len']} vs 我们 {op['text_len']})")
        elif wp["big_img"] and not op["big_img"] and op["text_len"] > 50:
            lines.append(f"p{p}: 我们可编辑排版更好，WPS偏整页图")
        elif not wp["big_img"] and op["big_img"]:
            lines.append(f"p{p}: WPS可编辑，我们偏整页图")

    score_wps = 0
    score_ours = 0
    for wp, op in zip(wps["pages"], ours["pages"]):
        # 可编辑性
        if op["text_len"] > wp["text_len"] + 50:
            score_ours += 2
        elif wp["text_len"] > op["text_len"] + 50:
            score_wps += 2
        # 版式/非整页图
        if not op["big_img"] and wp["big_img"] and op["text_len"] > 40:
            score_ours += 2
        elif not wp["big_img"] and op["big_img"]:
            score_wps += 2
        # 表格
        if op["tables"] > wp["tables"]:
            score_ours += 1
        elif wp["tables"] > op["tables"]:
            score_wps += 1
        # 水印
        if wp["preview"] and any(w in wp["preview"] for w in ("臻", "德厚")):
            score_ours += 1
        if op["preview"] and any(w in op["preview"] for w in ("臻", "德厚")):
            score_wps += 1

    return lines, score_wps, score_ours


def main():
    import os
    for p in (WPS, OURS):
        if not os.path.isfile(p):
            print("MISSING", p)
            return 1
    wps = analyze(WPS)
    ours = analyze(OURS)
    diffs, sw, so = verdict(wps, ours)

    print("=== SUMMARY ===")
    for k in ("size_mb", "media_count", "page_sections", "total_text_len", "tables", "pics", "huge_images", "wm_hits", "has_blue_stamp"):
        print(f"{k:16} WPS={wps[k]!s:20} OURS={ours[k]!s}")

    print("\n=== PER-PAGE ===")
    print(f"{'pg':>3} {'WPS_txt':>8} {'OUR_txt':>8} {'WPS_tbl':>7} {'OUR_tbl':>7} {'WPS_big':>7} {'OUR_big':>7}")
    for wp, op in zip(wps["pages"], ours["pages"]):
        print(
            f"{wp['page']:3d} {wp['text_len']:8d} {op['text_len']:8d} "
            f"{wp['tables']:7d} {op['tables']:7d} "
            f"{str(wp['big_img']):>7} {str(op['big_img']):>7}"
        )

    print("\n=== KEY DIFFS ===")
    for d in diffs:
        print(" ", d)
    print(f"\nHeuristic score: WPS={sw} OURS={so} (higher=better on editable/layout metrics)")

    print("\n=== SAMPLE PREVIEWS ===")
    for label, data in ("WPS", wps), ("OURS", ours):
        print(f"-- {label} page1 --")
        print(data["pages"][0]["preview"])
        if len(data["pages"]) > 9:
            print(f"-- {label} page10 --")
            print(data["pages"][9]["preview"][:120])


if __name__ == "__main__":
    raise SystemExit(main())