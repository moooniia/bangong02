#!/usr/bin/env python3
"""全站 API 冒烟测试 — 用真实样本文件逐项验证。"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("TOOLBOX_BASE", "http://139.196.28.78")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

SAMPLES = {
    "pdf": os.path.join(DESKTOP, "2.pdf"),
    "pdf2": os.path.join(DESKTOP, "1.pdf"),
    "png": os.path.join(DESKTOP, "1.png"),
    "docx": os.path.join(DESKTOP, "22222", "2026年安全工作任务清单.docx"),
}


def post(api, path, extra=None, field="file", timeout=300):
    boundary = "----Suite"
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower()
    ctype = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(ext, "application/octet-stream")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{os.path.basename(path)}"\r\n'
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
        BASE + api,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode()), round(time.time() - t0, 1)


def check(name, api, path, extra=None, timeout=300):
    if not os.path.exists(path):
        print(f"SKIP {name} (no file {path})")
        return None
    try:
        status, data, secs = post(api, path, extra, timeout=timeout)
        ok = status == 200 and data.get("success")
        print(f"{'OK' if ok else 'FAIL'} {name} {secs}s {data if not ok else data.get('filename','')}")
        return ok
    except urllib.error.HTTPError as e:
        print(f"FAIL {name} HTTP {e.code} {e.read().decode()[:120]}")
        return False
    except Exception as e:
        print(f"FAIL {name} {type(e).__name__} {e}")
        return False


def main():
    pdf = SAMPLES["pdf"] if os.path.exists(SAMPLES["pdf"]) else SAMPLES.get("pdf2")
    png = SAMPLES["png"] if os.path.exists(SAMPLES["png"]) else None
    docx = SAMPLES["docx"] if os.path.exists(SAMPLES["docx"]) else None
    results = []

    with urllib.request.urlopen(BASE + "/api/health", timeout=10) as r:
        print("health", r.read().decode())

    if pdf:
        results.append(check("pdf->word", "/api/convert", pdf, {"format": "docx"}, 600))
        results.append(check("pdf->excel", "/api/convert", pdf, {"format": "xlsx"}))
        results.append(check("pdf->ppt", "/api/convert", pdf, {"format": "pptx"}, 180))
        results.append(check("pdf watermark", "/api/pdf/watermark", pdf, {"text": "内部资料"}))
        results.append(check("pdf compress", "/api/pdf/compress", pdf))
        results.append(check("pdf rotate", "/api/pdf/rotate", pdf, {"angle": "90"}))
        results.append(check("pdf grayscale", "/api/pdf/grayscale", pdf))
        results.append(check("pdf to images", "/api/pdf/to-images", pdf))
        results.append(check("pdf encrypt", "/api/pdf/encrypt", pdf, {"password": "test1234"}))

    if docx:
        results.append(check("word->pdf", "/api/convert", docx, {"format": "pdf"}))

    if png:
        results.append(check("ocr image", "/api/ocr", png, {"lang": "auto", "output": "text"}, 120))

    ok = sum(1 for x in results if x)
    total = sum(1 for x in results if x is not None)
    print(f"\n=== {ok}/{total} passed ===")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()