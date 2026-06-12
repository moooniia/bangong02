#!/usr/bin/env python3
"""办公工具箱巡检 — 核心 API 冒烟，失败时飞书通知（webhook 或 OpenClaw 应用凭证）。"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("TOOLBOX_BASE", "http://127.0.0.1:5000")
CONFIG_PATH = os.environ.get("TOOLBOX_MONITOR_CONFIG", "/home/toolbox/monitor.env")
OPENCLAW_CONFIG = os.environ.get("OPENCLAW_CONFIG", "/root/.openclaw/openclaw.json")
FIXTURES = os.environ.get("TOOLBOX_FIXTURES", "/home/toolbox/fixtures")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")


def _sample(*names):
    for name in names:
        for base in (FIXTURES, DESKTOP):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
    return os.path.join(FIXTURES, names[0])


SAMPLES = {
    "pdf": _sample("2.pdf", "1.pdf"),
    "png": _sample("1.png"),
    "docx": _sample("sample.docx"),
}


def load_config():
    cfg = {}
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    for key in (
        "FEISHU_WEBHOOK",
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_RECEIVE_ID",
        "OPENCLAW_CONFIG",
    ):
        if os.environ.get(key):
            cfg[key] = os.environ[key].strip()
    return cfg


def load_openclaw_feishu(openclaw_path):
    path = openclaw_path or OPENCLAW_CONFIG
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        feishu = data.get("channels", {}).get("feishu", {})
        account = feishu.get("accounts", {}).get("default", {})
        app_id = account.get("appId", "").strip()
        app_secret = account.get("appSecret", "").strip()
        if not app_id or not app_secret:
            return None
        receive_id = ""
        allow_from = data.get("commands", {}).get("ownerAllowFrom", [])
        for item in allow_from:
            if isinstance(item, str) and item.startswith("feishu:"):
                receive_id = item.split(":", 1)[1]
                break
        return {"app_id": app_id, "app_secret": app_secret, "receive_id": receive_id}
    except Exception:
        return None


def post(api, path, extra=None, field="file", timeout=300):
    boundary = "----Monitor"
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


def post_json(api, payload, timeout=60):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + api,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode()), round(time.time() - t0, 1)


def check(name, api, path=None, extra=None, json_body=None, timeout=300):
    try:
        if json_body is not None:
            status, data, secs = post_json(api, json_body, timeout=timeout)
        else:
            if not path or not os.path.exists(path):
                return name, None, f"样本缺失: {path}"
            status, data, secs = post(api, path, extra, timeout=timeout)
        ok = status == 200 and data.get("success")
        detail = data.get("filename", "") if ok else str(data)[:200]
        return name, ok, f"{secs}s {detail}"
    except urllib.error.HTTPError as e:
        return name, False, f"HTTP {e.code} {e.read().decode()[:120]}"
    except Exception as e:
        return name, False, f"{type(e).__name__} {e}"


def _failure_text(failures):
    lines = ["【办公工具箱巡检失败】", f"站点: {BASE}", f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for name, detail in failures:
        lines.append(f"✗ {name}: {detail}")
    return "\n".join(lines)


def _briefing_text(results, passed, failed, skipped):
    lines = [
        "【办公工具箱每日简报】",
        f"站点: {BASE}",
        f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"结果: {passed} 通过 / {failed} 失败 / {skipped} 跳过",
        "",
    ]
    for name, ok, detail in results:
        if ok is True:
            lines.append(f"✓ {name}: {detail}")
        elif ok is False:
            lines.append(f"✗ {name}: {detail}")
        else:
            lines.append(f"- {name}: {detail}")
    if failed == 0:
        lines.append("")
        lines.append("一切正常。")
    return "\n".join(lines)


def notify_feishu_webhook(webhook, text):
    if not webhook or "xxxxxxxx" in webhook:
        return False
    payload = json.dumps({"msg_type": "text", "content": {"text": text}}).encode()
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()
    return True


def notify_feishu_app(app_id, app_secret, receive_id, text):
    if not app_id or not app_secret or not receive_id:
        return False
    token_req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(token_req, timeout=15) as r:
        token = json.loads(r.read().decode()).get("tenant_access_token", "")
    if not token:
        return False
    msg_req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        data=json.dumps({
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(msg_req, timeout=15) as r:
        resp = json.loads(r.read().decode())
    return resp.get("code", -1) == 0


def notify_feishu(text):
    cfg = load_config()
    webhook = cfg.get("FEISHU_WEBHOOK", "")
    if webhook:
        try:
            if notify_feishu_webhook(webhook, text):
                print("Feishu notified (webhook)")
                return True
        except Exception as e:
            print(f"Feishu webhook error: {e}")

    app_id = cfg.get("FEISHU_APP_ID", "")
    app_secret = cfg.get("FEISHU_APP_SECRET", "")
    receive_id = cfg.get("FEISHU_RECEIVE_ID", "")
    if not (app_id and app_secret):
        oc = load_openclaw_feishu(cfg.get("OPENCLAW_CONFIG", OPENCLAW_CONFIG))
        if oc:
            app_id = app_id or oc["app_id"]
            app_secret = app_secret or oc["app_secret"]
            receive_id = receive_id or oc["receive_id"]
    if app_id and app_secret and receive_id:
        try:
            if notify_feishu_app(app_id, app_secret, receive_id, text):
                print("Feishu notified (app)")
                return True
        except Exception as e:
            print(f"Feishu app error: {e}")
    return False


def run_checks():
    pdf = SAMPLES["pdf"] if os.path.exists(SAMPLES["pdf"]) else SAMPLES.get("pdf2")
    png = SAMPLES["png"] if os.path.exists(SAMPLES["png"]) else None
    docx = SAMPLES["docx"] if os.path.exists(SAMPLES["docx"]) else None

    checks = []

    if pdf:
        checks.extend([
            ("pdf->excel", "/api/convert", pdf, {"format": "xlsx"}, None, 120),
            ("pdf watermark", "/api/pdf/watermark", pdf, {"text": "巡检"}, None, 120),
            ("pdf compress", "/api/pdf/compress", pdf, None, None, 120),
            ("pdf to images", "/api/pdf/to-images", pdf, None, None, 180),
        ])
    if docx:
        checks.append(("word->pdf", "/api/convert", docx, {"format": "pdf"}, None, 120))
    # 扫描件 pdf->word 每次消耗 Volc OCR 页数；需要时手动测，部署冒烟默认跳过
    if pdf and os.environ.get("TOOLBOX_MONITOR_VOLC_WORD", "").strip() in ("1", "true", "yes"):
        checks.insert(0, ("pdf->word", "/api/convert", pdf, {"format": "docx"}, None, 600))
    if png:
        checks.append(("ocr image", "/api/ocr", png, {"lang": "auto", "output": "text"}, None, 120))

    results = []
    failures = []

    try:
        req = urllib.request.Request(BASE + "/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = r.status == 200
            detail = r.read().decode()[:80]
    except Exception as e:
        ok, detail = False, str(e)
    results.append(("health", ok, detail))
    if ok:
        print(f"OK   health {detail}")
    else:
        failures.append(("health", detail))
        print(f"FAIL health {detail}")

    for name, api, path, extra, body, timeout in checks:
        name, ok, detail = check(name, api, path, extra, body, timeout)
        results.append((name, ok, detail))
        if ok is False:
            failures.append((name, detail))
            print(f"FAIL {name} {detail}")
        elif ok is None:
            print(f"SKIP {name} {detail}")
        else:
            print(f"OK   {name} {detail}")

    passed = sum(1 for _, ok, _ in results if ok is True)
    failed = sum(1 for _, ok, _ in results if ok is False)
    skipped = sum(1 for _, ok, _ in results if ok is None)
    print(f"\n=== {passed} passed, {failed} failed, {skipped} skipped ===")
    return results, failures, passed, failed, skipped


def main():
    parser = argparse.ArgumentParser(description="办公工具箱巡检")
    parser.add_argument(
        "--briefing",
        action="store_true",
        help="发送每日简报（全绿也通知）",
    )
    args = parser.parse_args()
    results, failures, passed, failed, skipped = run_checks()

    if args.briefing:
        text = _briefing_text(results, passed, failed, skipped)
        if notify_feishu(text):
            print("Daily briefing sent")
        else:
            print("Feishu notify not configured — skip briefing")
        sys.exit(1 if failed else 0)

    if failures:
        if not notify_feishu(_failure_text(failures)):
            print("Feishu notify not configured — skip notify")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()