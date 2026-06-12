"""合同 GT 评测共用工具（OmniDocBench 思路，轻量实现）。"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_WATERMARK_PAT = re.compile(
    r"(臻子至善|李于至善|德厚生|正德厚生|哪生臻子|名厚生|于至善|厚生臻子|德厚|正德)"
)


def norm_text(s: str) -> str:
    s = re.sub(r"\s+", "", s or "")
    s = _WATERMARK_PAT.sub("", s)
    return s.strip()


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
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm_edit_distance(a: str, b: str) -> float:
    a, b = norm_text(a), norm_text(b)
    if not a and not b:
        return 0.0
    return levenshtein(a, b) / max(len(a), len(b), 1)


def edit_score(a: str, b: str) -> float:
    return round((1 - norm_edit_distance(a, b)) * 100, 2)


def box_to_poly(box: Dict) -> List[float]:
    x0 = float(box.get("x0", 0))
    y0 = float(box.get("y0", 0))
    x1 = float(box.get("x1", x0 + 10))
    y1 = float(box.get("y1", y0 + 10))
    return [x0, y0, x1, y0, x1, y1, x0, y1]


def table_rows_to_html(rows: List[List[str]]) -> str:
    parts = ["<table>"]
    for row in rows:
        parts.append("<tr>")
        for cell in row:
            c = (cell or "").replace("&", "&amp;").replace("<", "&lt;")
            parts.append(f"<td>{c}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def parse_html_table(html: str) -> List[List[str]]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html or "", re.I | re.S):
        cells = []
        for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.I | re.S):
            cells.append(norm_text(re.sub(r"<[^>]+>", "", td)))
        if cells:
            rows.append(cells)
    return rows


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
            parts.append(f"{prefix}C:{node.get('text', '')}")
        for ch in node.get("children") or []:
            parts.extend(flatten(ch, prefix + t[0].upper()))
        return parts

    sa, sb = flatten(a), flatten(b)
    s1, s2 = "|".join(sa), "|".join(sb)
    if not s1 and not s2:
        return 1.0
    dist = levenshtein(s1, s2)
    return 1.0 - dist / max(len(s1), len(s2), 1)


def teds_score(gt_html: str, pred_html: str) -> float:
    gr = parse_html_table(gt_html)
    pr = parse_html_table(pred_html)
    if not gr and not pr:
        return 100.0
    if not gr or not pr:
        return 0.0
    return round(tree_edit_similarity(table_to_tree(gr), table_to_tree(pr)) * 100, 2)