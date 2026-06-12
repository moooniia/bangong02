#!/usr/bin/env python3
import json
import os
import urllib.request

path = r"C:\Users\paz\Desktop\1.pdf"
boundary = "----TestB"
with open(path, "rb") as f:
    data = f.read()
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="1.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + data + (
    f"\r\n--{boundary}\r\n"
    f'Content-Disposition: form-data; name="format"\r\n\r\n'
    f"docx\r\n"
    f"--{boundary}--\r\n"
).encode()
req = urllib.request.Request(
    "http://139.196.28.78/api/convert",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        print("STATUS", r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print(e.read().decode())