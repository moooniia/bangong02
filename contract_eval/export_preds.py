#!/usr/bin/env python3
"""把转换结果导出为 OmniDocBench 预测格式（每页一个 .md）。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from contract_eval.common import table_rows_to_html


def _plain_pages_from_docx(path: str) -> list:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    parts = xml.split('w:br w:type="page"')
    pages = []
    for p in parts:
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)
        tables = []
        for tbl in re.findall(r"<w:tbl[\s\S]*?</w:tbl>", p):
            rows = []
            for tr in re.findall(r"<w:tr[\s\S]*?</w:tr>", tbl):
                cells = []
                for tc in re.findall(r"<w:tc[\s\S]*?</w:tc>", tr):
                    cells.append("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc)).strip())
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(table_rows_to_html(rows))
        body = "".join(texts).strip()
        snapshot = bool(re.search(r"<w:drawing", p)) and not body and not tables
        pages.append({"text": body, "tables": tables, "snapshot": snapshot})
    return pages


def _pages_from_volc_cache(cache_path: str) -> list:
    with open(cache_path, encoding="utf-8") as f:
        details = json.load(f)
    pages = []
    for p in details:
        texts, tables = [], []
        for b in p.get("textblocks") or []:
            lb = (b.get("label") or "").lower()
            t = (b.get("text") or "").strip()
            if lb in ("foot",):
                continue
            if "<table" in t.lower():
                tables.append(t)
            elif t:
                texts.append(t)
        md = p.get("page_md") or ""
        if md and not texts:
            md_clean = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", md)
            texts = [ln.strip() for ln in md_clean.splitlines() if ln.strip()]
        pages.append({
            "text": "\n\n".join(texts),
            "tables": tables,
        })
    return pages


def page_to_markdown(page: dict) -> str:
    chunks = []
    if page.get("text"):
        chunks.append(page["text"])
    for html in page.get("tables") or []:
        chunks.append(html)
    if page.get("snapshot"):
        chunks.append("<!-- page_snapshot_only -->")
    return "\n\n".join(chunks).strip() + "\n"


def export_preds(docx_path: str = "", cache_path: str = "", out_dir: str = ""):
    os.makedirs(out_dir, exist_ok=True)
    if docx_path and os.path.isfile(docx_path):
        pages = _plain_pages_from_docx(docx_path)
        source = "docx"
    elif cache_path and os.path.isfile(cache_path):
        pages = _pages_from_volc_cache(cache_path)
        source = "volc_cache"
    else:
        raise FileNotFoundError("need --docx or --cache")

    for i, p in enumerate(pages):
        path = os.path.join(out_dir, f"page_{i + 1:03d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page_to_markdown(p))
    print(f"exported {len(pages)} pages from {source} -> {out_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="1212")
    ap.add_argument("--docx", default="")
    ap.add_argument("--cache", default="")
    args = ap.parse_args()
    if not args.docx:
        args.docx = os.path.join(ROOT, f"{args.id}_full.docx")
    if not os.path.isfile(args.docx):
        args.docx = r"C:\Users\paz\Desktop\1212_full.docx"
    if not args.cache:
        args.cache = os.path.join(ROOT, f"{args.id}_detail_full.json")
    out = os.path.join(os.path.dirname(__file__), "preds", args.id)
    export_preds(docx_path=args.docx, cache_path=args.cache, out_dir=out)


if __name__ == "__main__":
    main()