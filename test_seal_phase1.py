#!/usr/bin/env python3
"""阶段1签章验收：上传 1212.pdf、检查路径、下载结果。"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import put, run  # noqa: E402

PDF = r"C:\Users\paz\Desktop\1212.pdf"
REMOTE_PDF = "/tmp/1212.pdf"
OUT_DOCX = r"C:\Users\paz\Desktop\1212_seal_phase1.docx"
API = "http://139.196.28.78/api/convert"


def main():
    put(PDF, REMOTE_PDF)
    code, out, err = run(
        f"pdftotext {REMOTE_PDF} - 2>/dev/null | wc -c; "
        f"python3.8 -c \""
        f"import subprocess; "
        f"r=subprocess.run(['pdftotext','{REMOTE_PDF}','-'],capture_output=True,text=True); "
        f"print('text_chars',len(r.stdout.strip())); "
        f"print('has_text',len(r.stdout.strip())>50)"
        f"\""
    )
    print("=== server pdf check ===")
    print(out or err)

    boundary = "----SealPhase1"
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
        API,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.loads(r.read().decode())
    print("=== convert ===")
    print(round(time.time() - t0, 1), "s", resp)

    fn = resp["filename"]
    url = f"http://139.196.28.78/api/download/{fn}"
    urllib.request.urlretrieve(url, OUT_DOCX)
    print("saved", OUT_DOCX, "bytes", os.path.getsize(OUT_DOCX))

    code, out, err = run(
        "journalctl -u toolbox -n 30 --no-pager | grep -E '1212|扫描|LibreOffice|火山' || true"
    )
    print("=== recent logs ===")
    print(out or err)


if __name__ == "__main__":
    main()