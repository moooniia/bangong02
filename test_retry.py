#!/usr/bin/env python3
import json, mimetypes, os, urllib.request

BASE = "http://139.196.28.78"

def post(api, path, extra=None):
    b = "----B"
    with open(path, "rb") as f: data = f.read()
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(path)}\"\r\n\r\n").encode() + data
    if extra:
        for k,v in extra.items():
            body += f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}".encode()
    body += f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(BASE+api, data=body, headers={"Content-Type":f"multipart/form-data; boundary={b}"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())

pdf = r"C:\Users\paz\Desktop\1.pdf"
img = r"C:\Users\paz\Desktop\测试题\职工之家  金伯玉.jpg"
for name, api, path, ex in [
    ("pdf-watermark", "/api/pdf/watermark", pdf, {"text":"内部资料"}),
    ("image-timestamp", "/api/image/timestamp", img, None),
    ("file-translate", "/api/translate/file", pdf, {"from":"zh-CN","to":"en","format":"txt"}),
]:
    try:
        r = post(api, path, ex)
        print(name, "OK" if r.get("success") else r.get("error"), r.get("filename"))
    except Exception as e:
        print(name, "ERR", e)