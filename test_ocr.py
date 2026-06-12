#!/usr/bin/env python3
import json
import os
import urllib.request

# 1) 远程检查 tesseract
import paramiko
HOST, USER, PW = "139.196.28.78", "root", "OpenClaw2026"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PW, timeout=30)
_, out, _ = c.exec_command("tesseract --list-langs 2>&1; python3.8 -c 'import pytesseract; print(pytesseract.get_languages())'")
print("=== SERVER LANGS ===")
print(out.read().decode())

# 2) 用用户桌面测试图调线上 OCR API
import mimetypes

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
        f'Content-Disposition: form-data; name="lang"\r\n\r\n'
        f"auto\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="output"\r\n\r\n'
        f"text\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        "http://139.196.28.78/api/ocr",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())

samples = [
    r"C:\Users\paz\Desktop\测试题\职工之家  金伯玉.jpg",
    r"C:\Users\paz\Desktop\测试题\职工之家   黄晨.png",
]
for p in samples:
    if not os.path.exists(p):
        print("missing", p)
        continue
    print("\n=== OCR:", os.path.basename(p), "===")
    try:
        res = ocr_file(p)
        text = res.get("text", res.get("error", res))
        print(text[:500] if isinstance(text, str) else text)
    except Exception as e:
        print("ERROR:", e)

c.close()