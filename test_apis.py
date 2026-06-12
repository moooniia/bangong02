#!/usr/bin/env python3
import json
import urllib.request

BASE = "http://139.196.28.78"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return r.status, r.read()[:200]

def post_json(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode())

pages = ["/", "/image-to-text.html", "/scan-to-text.html", "/extract-seal.html", "/text-translate.html"]
for p in pages:
    status, _ = get(p)
    print(f"{p}: {status}")

try:
    status, data = post_json("/api/translate", {"text": "你好世界", "from": "zh-CN", "to": "en"})
    print(f"translate: {status} -> {data}")
except Exception as e:
    print(f"translate error: {e}")