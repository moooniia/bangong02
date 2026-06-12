#!/usr/bin/env python3
import paramiko

HOST = "139.196.28.78"
USER = "root"
PASSWORD = "OpenClaw2026"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)

cmds = [
    "systemctl is-enabled toolbox",
    "systemctl is-active toolbox",
    """python3.8 -c "
import cv2
from deep_translator import GoogleTranslator
t = GoogleTranslator(source='zh-CN', target='en')
print('cv2', cv2.__version__)
print('translate', t.translate('你好世界'))
" """,
]
for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERR:", err)

client.close()