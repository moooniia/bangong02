#!/usr/bin/env python3
import json
import mimetypes
import os
import urllib.request

def ocr_file(path):
    boundary = "----Boundary7MA4YWxk"
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower()
    ctype = mimetypes.types_map.get(ext, "application/octet-stream")
    fname = os.path.basename(path)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="lang"\r\n\r\nauto\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="output"\r\n\r\n'
        f"text\r\n--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        "http://139.196.28.78/api/ocr",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())

samples = [
    r"C:\Users\paz\Desktop\1.png",
    r"C:\Users\paz\Desktop\1.pdf",
    r"C:\Users\paz\Desktop\2.pdf",
]
for p in samples:
    if not os.path.exists(p):
        continue
    print("\n===", p, "===")
    try:
        res = ocr_file(p)
        print(res.get("text", res.get("error"))[:600])
    except Exception as e:
        print("ERR", e)