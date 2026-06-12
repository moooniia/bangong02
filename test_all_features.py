#!/usr/bin/env python3
"""逐项测试新功能 API 和页面。"""
import json
import mimetypes
import os
import urllib.request

BASE = "http://139.196.28.78"

PAGES = [
    "/pdf-delete-pages.html", "/pdf-watermark.html", "/pdf-encrypt.html",
    "/pdf-decrypt.html", "/pdf-grayscale.html", "/pdf-extract-images.html",
    "/image-watermark.html", "/image-timestamp.html",
    "/file-translate.html", "/office-convert.html", "/file-rename.html",
]


def post_file(api, path, extra=None):
    boundary = "----TestBoundary"
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1]
    ctype = mimetypes.types_map.get(ext.lower(), "application/octet-stream")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + data
    if extra:
        for k, v in extra.items():
            body += (
                f"\r\n--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
                f"{v}\r\n"
            ).encode()
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + api, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


print("=== 页面检查 ===")
for p in PAGES:
    with urllib.request.urlopen(BASE + p, timeout=15) as r:
        print(p, r.status)

samples = {
    "pdf": r"C:\Users\paz\Desktop\1.pdf",
    "img": r"C:\Users\paz\Desktop\测试题\职工之家  金伯玉.jpg",
    "png": r"C:\Users\paz\Desktop\1.png",
}

tests = []
if os.path.exists(samples["pdf"]):
    tests += [
        ("/api/pdf/watermark", samples["pdf"], {"text": "内部资料"}),
        ("/api/pdf/delete-pages", samples["pdf"], {"pages": "2"}),
        ("/api/pdf/grayscale", samples["pdf"], None),
        ("/api/pdf/encrypt", samples["pdf"], {"password": "test1234"}),
    ]
if os.path.exists(samples["img"]):
    tests += [
        ("/api/image/watermark", samples["img"], {"text": "样本"}),
        ("/api/image/timestamp", samples["img"], None),
    ]
if os.path.exists(samples["png"]):
    tests += [
        ("/api/ocr", samples["png"], {"lang": "auto", "output": "text"}),
    ]

print("\n=== API 测试 ===")
enc_file = None
for api, path, extra in tests:
    name = api.split("/")[-1]
    try:
        res = post_file(api, path, extra)
        ok = res.get("success")
        print(f"[{'OK' if ok else 'FAIL'}] {name}: {res.get('filename') or res.get('error')}")
        if name == "encrypt" and ok:
            enc_file = res.get("filename")
    except Exception as e:
        print(f"[ERR] {name}: {e}")

if enc_file:
    try:
        # download encrypted to temp and test decrypt - skip, file deleted on download
        print("[SKIP] decrypt roundtrip (需手动验)")
    except Exception as e:
        print("[ERR] decrypt:", e)

if os.path.exists(samples.get("pdf", "")):
    try:
        res = post_file("/api/translate/file", samples["pdf"], {
            "from": "zh-CN", "to": "en", "format": "txt",
        })
        print(f"[{'OK' if res.get('success') else 'FAIL'}] file-translate: {res.get('filename') or res.get('error')}")
    except Exception as e:
        print(f"[ERR] file-translate: {e}")

print("\n完成")