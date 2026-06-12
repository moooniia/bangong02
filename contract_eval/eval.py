#!/usr/bin/env python3
"""合同 GT 评测：块级 Edit Distance + 表格 TEDS（OmniDocBench 轻量版）。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from contract_eval.common import (
    edit_score,
    norm_text,
    parse_html_table,
    teds_score,
)


def _load_gt(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_pred_md(pred_dir: str, page_no: int) -> str:
    p = os.path.join(pred_dir, f"page_{page_no + 1:03d}.md")
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8") as f:
        return f.read()


def _extract_pred_tables(md: str) -> list:
    return re.findall(r"<table[\s\S]*?</table>", md, re.I)


def _extract_pred_text(md: str) -> str:
    t = re.sub(r"<table[\s\S]*?</table>", "", md, flags=re.I)
    t = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _best_text_score(gt_txt: str, pred_pool: str) -> float:
    gt_n, pred_n = norm_text(gt_txt), norm_text(pred_pool)
    if not gt_n:
        return 100.0
    if not pred_n:
        return 0.0
    if gt_n in pred_n:
        return max(edit_score(gt_txt, pred_pool), 92.0)
    score = edit_score(gt_txt, pred_pool)
    if len(pred_n) > len(gt_n) * 1.5:
        step = max(1, len(gt_n) // 3)
        for i in range(0, max(1, len(pred_n) - len(gt_n)), step):
            window = pred_n[i: i + len(gt_n) + 80]
            score = max(score, edit_score(gt_txt, window))
    return score


def _match_blocks(gt_blocks: list, pred_text: str, pred_tables: list, pred_raw: str = ""):
    """按 GT 块顺序与预测做贪心匹配（简化 quick_match）。"""
    results = []
    pred_text_pool = pred_text
    ti = 0
    for gb in sorted(gt_blocks, key=lambda x: x.get("order", 0)):
        if gb.get("ignore"):
            continue
        cat = gb.get("category_type", "")
        cbt = (gb.get("attribute") or {}).get("contract_block", cat)
        if cat == "table" or gb.get("html"):
            gt_html = gb.get("html") or ""
            pred_html = pred_tables[ti] if ti < len(pred_tables) else ""
            ti += 1
            score = teds_score(gt_html, pred_html)
            note = "snapshot_page" if (not pred_html and "<!-- page_snapshot_only -->" in pred_raw) else None
            results.append({
                "type": "table",
                "contract_block": cbt,
                "metric": "teds",
                "score": score,
                "note": note or None,
                "gt_len": len(norm_text(re.sub(r"<[^>]+>", "", gt_html))),
                "pred_len": len(norm_text(re.sub(r"<[^>]+>", "", pred_html))),
            })
        else:
            gt_txt = gb.get("text") or ""
            if not gt_txt:
                continue
            # 在预测池里找最相似子串（简化：用全文比）
            score = _best_text_score(gt_txt, pred_text_pool)
            results.append({
                "type": "text",
                "contract_block": cbt,
                "metric": "edit",
                "score": score,
                "gt_len": len(norm_text(gt_txt)),
                "pred_len": len(norm_text(pred_text_pool)),
            })
    return results


def evaluate(gt_path: str, pred_dir: str) -> dict:
    gt_pages = _load_gt(gt_path)
    page_reports = []
    text_scores, table_scores = [], []

    for page in gt_pages:
        pno = page["page_info"]["page_no"]
        md = _load_pred_md(pred_dir, pno)
        pred_text = _extract_pred_text(md)
        pred_tables = _extract_pred_tables(md)
        blocks = _match_blocks(page.get("layout_dets") or [], pred_text, pred_tables, md)

        for b in blocks:
            if b["type"] == "table":
                table_scores.append(b["score"])
            else:
                text_scores.append(b["score"])

        page_reports.append({
            "page": pno + 1,
            "blocks": blocks,
            "page_text_avg": round(sum(x["score"] for x in blocks if x["type"] == "text") / max(1, sum(1 for x in blocks if x["type"] == "text")), 2),
            "page_table_avg": round(sum(x["score"] for x in blocks if x["type"] == "table") / max(1, sum(1 for x in blocks if x["type"] == "table")), 2),
        })

    text_avg = sum(text_scores) / max(len(text_scores), 1)
    table_avg = sum(table_scores) / max(len(table_scores), 1)
    overall = text_avg * 0.6 + table_avg * 0.4

    by_block = {}
    for pr in page_reports:
        for b in pr["blocks"]:
            k = b["contract_block"]
            by_block.setdefault(k, []).append(b["score"])

    return {
        "schema": "contract-eval-v1",
        "overall": round(overall, 2),
        "text_avg": round(text_avg, 2),
        "table_avg": round(table_avg, 2),
        "text_blocks": len(text_scores),
        "table_blocks": len(table_scores),
        "by_contract_block": {k: round(sum(v) / len(v), 2) for k, v in by_block.items()},
        "worst_blocks": sorted(
            [{"contract_block": b["contract_block"], "page": pr["page"], "score": b["score"], "type": b["type"]}
             for pr in page_reports for b in pr["blocks"]],
            key=lambda x: x["score"],
        )[:8],
        "pages": page_reports,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="1212")
    ap.add_argument("--gt", default="")
    ap.add_argument("--pred-dir", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    base = os.path.join(os.path.dirname(__file__))
    gt = args.gt or os.path.join(base, "gt", args.id, f"{args.id}_gt.json")
    pred = args.pred_dir or os.path.join(base, "preds", args.id)
    out = args.out or os.path.join(base, "results", f"{args.id}_eval.json")

    r = evaluate(gt, pred)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)

    print(f"overall={r['overall']} text={r['text_avg']} table={r['table_avg']}")
    print("worst blocks:")
    for w in r["worst_blocks"][:5]:
        print(f"  p{w['page']} {w['contract_block']}: {w['score']} ({w['type']})")
    print("saved", out)


if __name__ == "__main__":
    main()