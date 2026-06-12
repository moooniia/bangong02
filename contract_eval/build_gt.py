#!/usr/bin/env python3
"""从 PDF + 参考稿构建 OmniDocBench 格式合同真值（1212 及后续合同复用）。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from contract_eval.common import box_to_poly, norm_text, table_rows_to_html

# 合同页逻辑块类型（见 template.json）
PAGE_BLOCK_TYPES = {
    1: ["cover_header", "cover_title", "cover_parties"],
    2: ["contract_parties", "contract_clause"],
    3: ["sign_page"],
    4: ["tech_spec_title", "tech_spec_body"],
    5: ["tech_spec_body", "survey_table"],
    6: ["seal_page"],
    7: ["seal_page"],
    8: ["score_table"],
    9: ["policy_body"],
    10: ["product_table"],
    11: ["product_table"],
    12: ["closing_clause"],
}

WPS_MARKERS = [
    None,
    ["甲方：", "甲方:"],
    ["(签字页)", "签字页"],
    ["1. 工程概况", "1.工程概况", "围护监测技术规格书"],
    ["(1)运维楼", "运维楼"],
    None,
    None,
    ["服务管理考评", "考评打分表"],
    ["供应商负面行为处理规则", "供应商负面"],
    ["60IT硬件", "60IT硬件产品"],
    ["108电源", "108电源及动力环境"],
    ["第八条", "第八条  本协议", "第八条本协议"],
]


def _plain_docx(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def _extract_tables(path: str):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    tables = []
    for tbl in re.findall(r"<w:tbl[\s\S]*?</w:tbl>", xml):
        rows = []
        for tr in re.findall(r"<w:tr[\s\S]*?</w:tr>", tbl):
            cells = []
            for tc in re.findall(r"<w:tc[\s\S]*?</w:tc>", tr):
                t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc))
                cells.append(t.strip())
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _find_marker(text: str, candidates: list, start: int = 0) -> int:
    best = -1
    for m in candidates or []:
        pos = text.find(m, start)
        if pos >= 0 and (best < 0 or pos < best):
            best = pos
    return best


def _split_ref_pages(doc_xml_text: str, n: int = 12) -> list:
    full = doc_xml_text
    points = [0]
    search_from = 0
    for idx, markers in enumerate(WPS_MARKERS):
        if idx == 0:
            continue
        if idx == 5:
            pos = _find_marker(full, ["(签章页)", "签章页"], search_from)
        elif idx == 6:
            first = points[-1]
            pos = _find_marker(full, ["(签章页)", "签章页"], first + 5)
            if pos == first:
                pos = _find_marker(full, ["服务管理考评", "考评打分表"], first + 5)
        elif markers:
            pos = _find_marker(full, markers, search_from)
        else:
            pos = -1
        if pos > points[-1]:
            points.append(pos)
            search_from = pos + 1
    points = sorted(set(points))
    segs = []
    for i, start in enumerate(points):
        end = points[i + 1] if i + 1 < len(points) else len(full)
        segs.append(full[start:end].strip())
    while len(segs) < n and segs:
        idx = max(range(len(segs)), key=lambda k: len(segs[k]))
        s = segs.pop(idx)
        mid = len(s) // 2
        segs.insert(idx, s[mid:].strip())
        segs.insert(idx, s[:mid].strip())
    return segs[:n]


def _clean_gt_text(s: str) -> str:
    s = s or ""
    s = s.replace("\u3000", " ")
    s = re.sub(r"56生态", "5G生态", s)
    s = re.sub(r"勤察|粉察", "勘察", s)
    s = re.sub(r"CNCCT[BD]-SS", "CMCCTD-SS", s)
    s = re.sub(r"&lt;", "<", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _render_pdf_images(pdf_path: str, out_dir: str, dpi: int = 200):
    import fitz

    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    sizes = []
    for i in range(doc.page_count):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        name = f"page_{i + 1:03d}.png"
        pix.save(os.path.join(out_dir, name))
        sizes.append((pix.width, pix.height))
    doc.close()
    return sizes


def _load_ocr_boxes(cache_path: str) -> list:
    if not os.path.isfile(cache_path):
        return [[] for _ in range(12)]
    with open(cache_path, encoding="utf-8") as f:
        pages = json.load(f)
    out = []
    for p in pages:
        boxes = []
        for b in p.get("textblocks") or []:
            lb = (b.get("label") or "").lower()
            if lb in ("foot", "image"):
                continue
            t = _clean_gt_text(b.get("text") or "")
            if not t or lb == "header" and t.startswith("CMCCTD") and len(t) < 24:
                if lb != "header":
                    pass
            if t and not re.fullmatch(r"\d{1,3}", t):
                boxes.append({"label": lb, "text": t, "box": b.get("box") or {}})
        out.append(boxes)
    return out


def _make_block(anno_id: int, order: int, category: str, text: str = "", html: str = "", box=None, ignore=False):
    box = box or {"x0": 40, "y0": 40 + order * 30, "x1": 800, "y1": 70 + order * 30}
    item = {
        "category_type": category,
        "poly": box_to_poly(box),
        "ignore": ignore,
        "order": order,
        "anno_id": anno_id,
        "attribute": {"contract_block": category},
    }
    if html:
        item["html"] = html
    if text:
        item["text"] = text
    return item


def _split_text_blocks(page_text: str, block_types: list) -> list:
    """把页文本切成逻辑块（段落级）。"""
    page_text = _clean_gt_text(page_text)
    if not page_text:
        return [(bt, "") for bt in block_types]

    # 表格页整段作为一块
    if any(t.endswith("_table") for t in block_types) and len(block_types) == 1:
        return [(block_types[0], page_text)]

    parts = re.split(r"(?<=[。；;！!？?])\s*", page_text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [page_text]

    if len(block_types) == 1:
        return [(block_types[0], page_text)]

    if len(parts) >= len(block_types):
        chunk = max(1, len(parts) // len(block_types))
        out = []
        for i, bt in enumerate(block_types):
            seg = parts[i * chunk: (i + 1) * chunk if i < len(block_types) - 1 else len(parts)]
            out.append((bt, " ".join(seg)))
        return out

    out = []
    for i, bt in enumerate(block_types):
        out.append((bt, parts[i] if i < len(parts) else ""))
    return out


def build_gt(pdf_path: str, ref_docx: str, cache_path: str, out_json: str, images_dir: str):
    sizes = _render_pdf_images(pdf_path, images_dir)
    ref_pages = _split_ref_pages(_plain_docx(ref_docx))
    tables = _extract_tables(ref_docx)
    ocr_boxes = _load_ocr_boxes(cache_path)

    # 四张表按合同页映射
    table_by_page = {5: 0, 8: 1, 10: 2, 11: 3}

    pages = []
    anno = 0
    for pi in range(12):
        pw, ph = sizes[pi] if pi < len(sizes) else (1654, 2339)
        page_text = _clean_gt_text(ref_pages[pi] if pi < len(ref_pages) else "")
        block_types = PAGE_BLOCK_TYPES.get(pi + 1, ["text_block"])

        layout_dets = []
        order = 0

        if pi + 1 in table_by_page and table_by_page[pi + 1] < len(tables):
            ti = table_by_page[pi + 1]
            html = table_rows_to_html(tables[ti])
            bt = block_types[-1] if block_types else "table"
            layout_dets.append(_make_block(anno, order, "table", html=html, box={"x0": 50, "y0": 200, "x1": pw - 50, "y1": ph - 100}))
            anno += 1
            order += 1
            # 非表块用剩余文本
            text_types = [t for t in block_types if not t.endswith("_table")]
            if text_types and page_text:
                for bt, txt in _split_text_blocks(page_text, text_types):
                    if txt:
                        layout_dets.append(_make_block(anno, order, "text_block", text=txt, box={"x0": 50, "y0": 80, "x1": pw - 50, "y1": 180}))
                        layout_dets[-1]["attribute"]["contract_block"] = bt
                        anno += 1
                        order += 1
        else:
            for bt, txt in _split_text_blocks(page_text, block_types):
                if not txt:
                    continue
                box = {"x0": 50, "y0": 60 + order * 40, "x1": pw - 50, "y1": 100 + order * 40}
                if pi < len(ocr_boxes) and ocr_boxes[pi]:
                    ob = ocr_boxes[pi][min(order, len(ocr_boxes[pi]) - 1)]
                    if ob.get("box"):
                        box = ob["box"]
                layout_dets.append(_make_block(anno, order, "text_block", text=txt, box=box))
                layout_dets[-1]["attribute"]["contract_block"] = bt
                anno += 1
                order += 1

        pages.append({
            "layout_dets": layout_dets,
            "page_info": {
                "page_no": pi,
                "height": ph,
                "width": pw,
                "image_path": f"images/page_{pi + 1:03d}.png",
                "page_attribute": {
                    "data_source": "service_contract",
                    "language": "simplified_chinese",
                    "watermark": "true",
                    "fuzzy_scan": "true",
                },
            },
            "extra": {"relation": []},
        })

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print("gt pages", len(pages), "blocks", sum(len(p["layout_dets"]) for p in pages))
    print("saved", out_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="1212")
    ap.add_argument("--pdf", default=r"C:\Users\paz\Desktop\1212.pdf")
    ap.add_argument("--ref-docx", default=r"C:\Users\paz\Desktop\1212.docx", help="参考稿（用于起草真值，需人工核对 PDF）")
    ap.add_argument("--cache", default=os.path.join(ROOT, "1212_detail_full.json"))
    args = ap.parse_args()
    base = os.path.join(os.path.dirname(__file__), "gt", args.id)
    build_gt(
        args.pdf,
        args.ref_docx,
        args.cache,
        os.path.join(base, f"{args.id}_gt.json"),
        os.path.join(base, "images"),
    )


if __name__ == "__main__":
    main()