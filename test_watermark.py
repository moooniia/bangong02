#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

PDF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\paz\Desktop\2.pdf"
TEXT = sys.argv[2] if len(sys.argv) > 2 else "内部资料"
BASE = "http://139.196.28.78"

boundary = "----WM"
with open(PDF, "rb") as f:
    data = f.read()
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(PDF)}"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + data + (
    f"\r\n--{boundary}\r\n"
    f'Content-Disposition: form-data; name="text"\r\n\r\n'
    f"{TEXT}\r\n"
    f"--{boundary}--\r\n"
).encode()
req = urllib.request.Request(
    f"{BASE}/api/pdf/watermark",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=120) as r:
    print(r.read().decode())