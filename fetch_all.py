#!/usr/bin/env python3
import os
import paramiko

HOST = "139.196.28.78"
USER = "root"
PASSWORD = "OpenClaw2026"
LOCAL_BASE = r"C:\Users\paz\toolbox-work\server"
REMOTE_BASE = "/home/toolbox"

FILES = [
    "backend/app.py",
    "frontend/index.html",
    "frontend/pdf-to-word.html",
    "frontend/pdf-to-excel.html",
    "frontend/pdf-to-ppt.html",
    "frontend/word-to-pdf.html",
    "frontend/excel-to-pdf.html",
    "frontend/ppt-to-pdf.html",
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
sftp = client.open_sftp()

for rel in FILES:
    remote = f"{REMOTE_BASE}/{rel}"
    local = os.path.join(LOCAL_BASE, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(local), exist_ok=True)
    sftp.get(remote, local)
    print(f"Fetched {rel}")

sftp.close()
client.close()
print("Done")