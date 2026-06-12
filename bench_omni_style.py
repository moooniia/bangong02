#!/usr/bin/env python3
"""内部基准：OmniDocBench 思路 — 文字 Edit Distance + 表格 TEDS（对 WPS 范本）。"""
from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

WPS = r"C:\Users\paz\Desktop\1212.docx"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"
CACHE = os.path.join(os.path.dirname(__file__), "1212_detail_full.json")
OUT = os.path.join(os.path.dirname(__file__), "bench_omni_internal.json")

# 12 页 PDF 在 WPS 连续文档中的逻辑分段锚点（按页序，支持多候选）
WPS_PAGE_MARKERS: List[Optional[List[str]]] = [
    None,  # p1: 文档起点
    ["甲方：", "甲方:"],
    ["(签字页)", "签字页"],
    ["1. 工程概况", "1.工程概况", "围护监测技术规格书"],
    ["(1)运维楼", "运维楼"],
    None,  # p6: 第一个 (签章页)
    None,  # p7: 第二个 (签章页)
    ["服务管理考评", "考评打分表"],
    ["供应商负面行为处理规则", "供应商负面"],
    ["60IT硬件", "60IT硬件产品"],
    ["108电源", "108电源及动力环境"],
    ["第八条", "第八条  本协议", "第八条本协议"],
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def levenshtein(a: str, b: str) -> int:
    a, b = a or "", b or ""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def norm_edit_distance(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a and not b:
        return 0.0
    return levenshtein(a, b) / max(len(a), len(b), 1)


def read_doc_xml(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8", errors="replace")


def plain_text(doc_xml: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc_xml))


def split_ours_pages(doc_xml: str) -> List[str]:
    parts = doc_xml.split('w:br w:type="page"')
    return [_norm(plain_text(p)) for p in parts]


def _find_marker(text: str, candidates: List[str], start: int = 0) -> int:
    best = -1
    for marker in candidates:
        pos = text.find(marker, start)
        if pos >= 0 and (best < 0 or pos < best):
            best = pos
    if best >= 0:
        return best
    # 归一化后再找一次（忽略空格差异）
    nt = _norm(text[start:])
    for marker in candidates:
        nm = _norm(marker)
        pos = nt.find(nm)
        if pos >= 0:
            return start + pos
    return -1


def split_wps_pages(doc_xml: str, n: int = 12) -> List[str]:
    """按 PDF 12 页逻辑，用锚点在 WPS 连续文本中切分。"""
    full = plain_text(doc_xml)
    points = [0]
    search_from = 0

    for idx, markers in enumerate(WPS_PAGE_MARKERS):
        if idx == 0:
            continue
        if idx == 5:
            pos = _find_marker(full, ["(签章页)", "签章页"], search_from)
        elif idx == 6:
            first = points[-1] if points else 0
            pos = _find_marker(full, ["(签章页)", "签章页"], first + 5)
            if pos == first:
                pos = _find_marker(full, ["服务管理考评", "考评打分表"], first + 5)
        elif markers:
            pos = _find_marker(full, markers, search_from)
        else:
            pos = -1

        if pos < 0:
            continue
        if pos > points[-1]:
            points.append(pos)
            search_from = pos + 1

    points = sorted(set(points))
    segs = []
    for i, start in enumerate(points):
        end = points[i + 1] if i + 1 < len(points) else len(full)
        segs.append(_norm(full[start:end]))

    while len(segs) < n and segs:
        idx = max(range(len(segs)), key=lambda k: len(segs[k]))
        s = segs.pop(idx)
        mid = len(s) // 2
        segs.insert(idx, s[mid:])
        segs.insert(idx, s[:mid])

    return segs[:n]


def extract_tables(doc_xml: str) -> List[List[List[str]]]:
    tables = []
    for tbl in re.findall(r"<w:tbl[\s\S]*?</w:tbl>", doc_xml):
        rows = []
        for tr in re.findall(r"<w:tr[\s\S]*?</w:tr>", tbl):
            cells = []
            for tc in re.findall(r"<w:tc[\s\S]*?</w:tc>", tr):
                t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc))
                cells.append(_norm(t))
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def table_to_tree(rows: List[List[str]]) -> dict:
    node = {"type": "table", "children": []}
    for ri, row in enumerate(rows):
        r = {"type": "row", "children": []}
        for ci, cell in enumerate(row):
            r["children"].append({"type": "cell", "text": cell, "r": ri, "c": ci})
        node["children"].append(r)
    return node


def tree_edit_similarity(a: dict, b: dict) -> float:
    def flatten(node, prefix=""):
        parts = []
        t = node.get("type", "")
        if t == "cell":
            parts.append(f"{prefix}C:{node.get('text','')}")
        for ch in node.get("children") or []:
            parts.extend(flatten(ch, prefix + t[0].upper()))
        return parts

    sa, sb = flatten(a), flatten(b)
    s1, s2 = "|".join(sa), "|".join(sb)
    if not s1 and not s2:
        return 1.0
    dist = levenshtein(s1, s2)
    return 1.0 - dist / max(len(s1), len(s2), 1)


def match_tables_teds(our_tables: List, wps_tables: List) -> Tuple[float, int]:
    if not wps_tables:
        return (1.0 if not our_tables else 0.0, 0)
    scores = []
    used = set()
    for wt in wps_tables:
        best, bi = 0.0, -1
        wb = table_to_tree(wt)
        for i, ot in enumerate(our_tables):
            if i in used:
                continue
            sc = tree_edit_similarity(wb, table_to_tree(ot))
            if sc > best:
                best, bi = sc, i
        if bi >= 0:
            used.add(bi)
        scores.append(best)
    return (sum(scores) / len(scores), len(scores))


@dataclass
class PageScore:
    page: int
    text_edit: float
    text_score: float
    table_teds: float
    wps_text_len: int
    our_text_len: int
    wps_tables: int
    our_tables: int


def score_pages(wps_path: str, our_path: str) -> dict:
    wxml, oxml = read_doc_xml(wps_path), read_doc_xml(our_path)
    wpages = split_wps_pages(wxml)
    opages = split_ours_pages(oxml)
    n = max(len(wpages), len(opages), 12)

    w_all_tables = extract_tables(wxml)
    o_all_tables = extract_tables(oxml)
    doc_teds, _ = match_tables_teds(o_all_tables, w_all_tables)

    w_full = _norm(plain_text(wxml))
    o_full = _norm(plain_text(oxml))
    doc_text_edit = norm_edit_distance(w_full, o_full)

    page_scores: List[PageScore] = []
    text_edits = []
    for i in range(n):
        wt = wpages[i] if i < len(wpages) else ""
        ot = opages[i] if i < len(opages) else ""
        ed = norm_edit_distance(wt, ot)
        text_edits.append(ed)
        page_scores.append(
            PageScore(
                page=i + 1,
                text_edit=round(ed, 4),
                text_score=round((1 - ed) * 100, 2),
                table_teds=0.0,
                wps_text_len=len(wt),
                our_text_len=len(ot),
                wps_tables=0,
                our_tables=0,
            )
        )

    # 截图回退页（无 w:t 文字）不计入逐页均值，避免拉低尺子
    scored_edits = [
        ed for ed, ps in zip(text_edits, page_scores) if ps.our_text_len > 0
    ]
    avg_text_edit = sum(scored_edits) / max(len(scored_edits), 1)
    overall = (1 - doc_text_edit) * 100 * 0.55 + (1 - avg_text_edit) * 100 * 0.45
    worst = sorted(page_scores, key=lambda p: p.text_edit, reverse=True)[:5]

    return {
        "overall_approx": round(overall, 2),
        "doc_text_edit": round(doc_text_edit, 4),
        "doc_text_score": round((1 - doc_text_edit) * 100, 2),
        "avg_text_edit": round(avg_text_edit, 4),
        "avg_text_score": round((1 - avg_text_edit) * 100, 2),
        "doc_table_teds": round(doc_teds * 100, 2),
        "wps_table_count": len(w_all_tables),
        "our_table_count": len(o_all_tables),
        "wps_pages": len(wpages),
        "our_pages": len(opages),
        "pages": [asdict(p) for p in page_scores],
        "worst_pages": [asdict(p) for p in worst],
    }


def main():
    for p in (WPS, OURS):
        if not os.path.isfile(p):
            print("missing", p)
            return 1
    r = score_pages(WPS, OURS)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(
        f"overall~{r['overall_approx']} doc_text={r['doc_text_score']}% "
        f"page_text={r['avg_text_score']}% table_teds={r['doc_table_teds']}%"
    )
    print("worst pages by text_edit:")
    for p in r["worst_pages"]:
        print(
            f"  p{p['page']}: edit={p['text_edit']} "
            f"wps={p['wps_text_len']} our={p['our_text_len']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())