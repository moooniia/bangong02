#!/usr/bin/env python3
"""转换 1212 并与 WPS 版对比核心指标。"""
import json
import os
import re
import sys
import urllib.request
import zipfile

WPS = r"C:\Users\paz\Desktop\1212.docx"
PDF = r"C:\Users\paz\Desktop\1212.pdf"
OURS = r"C:\Users\paz\Desktop\1212_full.docx"
API = "http://139.196.28.78/api/convert"

TARGETS = {
    "total_text_len": 7500,
    "tables": 20,
    "fullpage_images": 1,
    "size_mb_max": 2.0,
}


def convert():
    boundary = "----Bench1212"
    with open(PDF, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="1212.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="format"\r\n\r\n'
        f"docx\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read().decode())
    url = f"http://139.196.28.78/api/download/{resp['filename']}"
    urllib.request.urlretrieve(url, OURS)


def metrics(path):
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", errors="replace")
    text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc))
    extents = [int(x) for x in re.findall(r'cx="(\d+)"', doc)]
    return {
        "total_text_len": len(text.strip()),
        "tables": doc.count("<w:tbl"),
        "fullpage_images": sum(1 for x in extents if x > 5_000_000),
        "pics": doc.count("<pic:pic"),
        "size_mb": round(os.path.getsize(path) / 1048576, 2),
        "keywords": {
            k: k in text
            for k in (
                "签字页", "签章页", "签字/盖章", "第八条",
                "工程概况", "60IT硬件", "108", "电源及动力",
            )
        },
    }


def main():
    if not os.path.isfile(WPS):
        print("missing WPS ref", WPS)
        return 1
    print("converting...")
    convert()
    w = metrics(WPS)
    o = metrics(OURS)
    print("\n=== WPS ===")
    for k, v in w.items():
        print(f"  {k}: {v}")
    print("\n=== OURS ===")
    for k, v in o.items():
        print(f"  {k}: {v}")

    ok = True
    print("\n=== TARGET CHECK ===")
    checks = [
        ("total_text_len", o["total_text_len"] >= TARGETS["total_text_len"], f"{o['total_text_len']} >= {TARGETS['total_text_len']}"),
        ("tables", o["tables"] >= TARGETS["tables"], f"{o['tables']} >= {TARGETS['tables']}"),
        ("fullpage_images", o["fullpage_images"] <= TARGETS["fullpage_images"], f"{o['fullpage_images']} <= {TARGETS['fullpage_images']}"),
        ("size_mb", o["size_mb"] <= TARGETS["size_mb_max"], f"{o['size_mb']} <= {TARGETS['size_mb_max']}"),
    ]
    for name, passed, detail in checks:
        mark = "OK" if passed else "FAIL"
        print(f"  [{mark}] {name}: {detail}")
        ok = ok and passed

    ratio = o["total_text_len"] / max(w["total_text_len"], 1)
    print(f"\ntext_ratio vs WPS: {ratio:.1%}")
    return 0 if ok and ratio >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())