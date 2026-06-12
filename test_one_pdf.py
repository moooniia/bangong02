#!/usr/bin/env python3
import os
import sys
import time
import urllib.error
import urllib.request

PDF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\paz\Desktop\1.pdf"
URL = sys.argv[2] if len(sys.argv) > 2 else "http://139.196.28.78/api/convert"
TIMEOUT = int(sys.argv[3]) if len(sys.argv) > 3 else 180

if not os.path.exists(PDF):
    print("FILE_NOT_FOUND", PDF)
    raise SystemExit(1)

print("file", PDF)
print("size", os.path.getsize(PDF))

boundary = "----TestB"
with open(PDF, "rb") as f:
    data = f.read()
name = os.path.basename(PDF)
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + data + (
    f"\r\n--{boundary}\r\n"
    f'Content-Disposition: form-data; name="format"\r\n\r\n'
    f"docx\r\n"
    f"--{boundary}--\r\n"
).encode()
req = urllib.request.Request(
    URL,
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        print("STATUS", r.status, "secs", round(time.time() - t0, 1))
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP", e.code, "secs", round(time.time() - t0, 1))
    print(e.read().decode())
except Exception as e:
    print(type(e).__name__, e, "secs", round(time.time() - t0, 1))