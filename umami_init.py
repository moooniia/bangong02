#!/usr/bin/env python3
"""初始化 Umami：创建站点、写入 analytics.js。"""
import json
import os
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:3000"
USER = os.environ.get("UMAMI_ADMIN_USER", "admin")
PASS = os.environ.get("UMAMI_ADMIN_PASS", "umami")
SITE_URL = os.environ.get("UMAMI_SITE_URL", "http://139.196.28.78")
ANALYTICS = "/home/toolbox/frontend/assets/analytics.js"
CREDS = "/home/toolbox/umami/credentials.txt"


def call(path, data=None, headers=None, method=None):
    body = json.dumps(data).encode() if data is not None else None
    h = {}
    if data is not None:
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers=h,
        method=method or ("POST" if data is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {"error": e.code}
        except Exception:
            payload = {"error": raw[:200]}
        return e.code, payload


if os.path.isfile(CREDS):
    with open(CREDS, encoding="utf-8") as f:
        for line in f:
            if line.startswith("password="):
                PASS = line.split("=", 1)[1].strip()
                break

code, resp = call("/api/auth/login", {"username": USER, "password": PASS})
if code != 200 or not resp.get("token"):
    raise SystemExit(f"login failed: {resp}")

token = resp["token"]
headers = {"Authorization": f"Bearer {token}"}
password = PASS

code, resp = call("/api/websites", headers=headers)
websites = resp if isinstance(resp, list) else resp.get("data", [])
website_id = None
for w in websites:
    if w.get("domain") == SITE_URL or w.get("name") == "办公工具箱":
        website_id = w.get("id") or w.get("websiteId")
        break

if not website_id:
    code, resp = call(
        "/api/websites",
        {"name": "办公工具箱", "domain": SITE_URL, "enableUrlCollection": True},
        headers,
    )
    if code not in (200, 201):
        raise SystemExit(f"create website failed: {resp}")
    website_id = resp.get("id") or resp.get("websiteId")

if not website_id:
    raise SystemExit(f"no website id: {resp}")

with open(ANALYTICS, encoding="utf-8") as f:
    js = f.read()
js = js.replace("__UMAMI_WEBSITE_ID__", website_id)
with open(ANALYTICS, "w", encoding="utf-8") as f:
    f.write(js)

with open(CREDS, "w", encoding="utf-8") as f:
    f.write(f"dashboard={SITE_URL}/dashboard\n")
    f.write(f"username={USER}\n")
    f.write(f"password={password}\n")
    f.write(f"website_id={website_id}\n")

print("website_id", website_id)
print("credentials", CREDS)