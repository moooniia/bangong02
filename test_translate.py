#!/usr/bin/env python3
import paramiko

HOST = "139.196.28.78"
USER = "root"
PASSWORD = "OpenClaw2026"

script = r"""
python3.8 << 'PYEOF'
import urllib.parse, urllib.request, json

def translate(text, fr, to):
    q = urllib.parse.quote(text)
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair={fr}|{to}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read().decode())
        return data.get("responseData", {}).get("translatedText"), data.get("responseStatus")

pairs = [
    ("你好世界", "zh-CN", "en"),
    ("hello", "en", "zh-CN"),
    ("こんにちは", "ja", "zh-CN"),
    ("hello", "autodetect", "zh-CN"),
]
for text, fr, to in pairs:
    r, status = translate(text, fr, to)
    print(fr, "->", to, ":", r, "status:", status)
PYEOF
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
stdin, stdout, stderr = client.exec_command(script, timeout=60)
print(stdout.read().decode())
client.close()