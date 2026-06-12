#!/usr/bin/env python3
"""完整转换 1212.pdf 并自验 12 页效果。"""
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile

PDF = r"C:\Users\paz\Desktop\1212.pdf"
OUT = r"C:\Users\paz\Desktop\1212_full.docx"
API = "http://139.196.28.78/api/convert"


def convert_pdf(pdf_path, out_docx):
    boundary = "----Full1212"
    with open(pdf_path, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(pdf_path)}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="format"\r\n\r\n'
        f"docx\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read().decode())
    url = f"http://139.196.28.78/api/download/{resp['filename']}"
    urllib.request.urlretrieve(url, out_docx)
    return out_docx


def split_pages(doc_xml):
    parts = doc_xml.split('w:br w:type="page"')
    return parts


def page_stats(page_xml):
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", page_xml)
    text = "".join(texts).strip()
    pics = page_xml.count("<pic:pic")
    # 大图：单段内多图或超宽图（启发式：含 drawing 且文字很少）
    big_snap = bool(
        pics >= 1
        and len(text) < 80
        and ("wp:extent" in page_xml)
        and re.search(r'cx="[0-9]{7,}"', page_xml)
    )
    editable_runs = sum(1 for t in texts if t.strip())
    return {
        "text_len": len(text),
        "pics": pics,
        "big_snapshot": big_snap,
        "text_preview": text[:120].replace("\n", " "),
        "has_table": "<w:tbl" in page_xml,
    }


def check_all_pages(docx_path, expected_pages=12):
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read("word/document.xml").decode("utf-8", errors="replace")
    pages = split_pages(doc)
    if len(pages) < expected_pages:
        pages = [doc]  # fallback single blob
    issues = []
    ok = []
    stats = []
    for i, pxml in enumerate(pages[:expected_pages], 1):
        st = page_stats(pxml)
        stats.append({"page": i, **st})
        if st["text_len"] < 15 and not st["has_table"]:
            issues.append(f"第{i}页几乎无文字")
        elif st["big_snapshot"] and st["text_len"] < 40:
            issues.append(f"第{i}页疑似整页截图为主")
        else:
            ok.append(f"第{i}页有可编辑内容(len={st['text_len']}, pics={st['pics']})")

    wm_frag = re.search(r"臻子|至善|德厚|李于|厚生", doc)
    if wm_frag:
        issues.append("文档仍含水印碎片")
    else:
        ok.append("水印文字已滤除")

    if len(pages) >= expected_pages:
        ok.append(f"分页 {len(pages)} 段")
    else:
        issues.append(f"分页不足(仅{len(pages)}段)")

    return {"ok": ok, "issues": issues, "stats": stats, "page_count": len(pages)}


def main():
    if not os.path.isfile(PDF):
        print("missing", PDF)
        return 1
    print("converting", PDF, "->", OUT)
    convert_pdf(PDF, OUT)
    print("saved", OUT, "size", os.path.getsize(OUT))
    r = check_all_pages(OUT)
    print("\n=== OK ===")
    for x in r["ok"]:
        print(" ", x)
    print("\n=== ISSUES ===")
    for x in r["issues"]:
        print(" ", x)
    print("\n=== PAGE STATS ===")
    for s in r["stats"]:
        print(
            f" p{s['page']}: text={s['text_len']} pics={s['pics']} "
            f"snap={s['big_snapshot']} | {s['text_preview'][:80]}"
        )
    return 0 if not r["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())