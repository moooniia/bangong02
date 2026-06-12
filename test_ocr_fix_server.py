#!/usr/bin/env python3
import os
import paramiko

HOST, USER, PW = "139.196.28.78", "root", "OpenClaw2026"
local_png = r"C:\Users\paz\Desktop\1.png"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PW, timeout=30)

# upload new ocr_utils and app.py first
sftp = c.open_sftp()
for f in ['ocr_utils.py', 'app.py']:
    sftp.put(
        rf"C:\Users\paz\toolbox-work\server\backend\{f}",
        f"/home/toolbox/backend/{f}",
    )
sftp.put(local_png, "/tmp/1.png")
sftp.close()

_, o, e = c.exec_command(
    "systemctl restart toolbox && sleep 2 && python3.8 << 'PYEOF'\n"
    "import sys\nsys.path.insert(0,'/home/toolbox/backend')\n"
    "from ocr_utils import ocr_image\n"
    "t = ocr_image('/tmp/1.png')\n"
    "print(t[:1200])\n"
    "print('---LEN', len(t))\n"
    "import re\n"
    "c = re.sub(r'\\s+','',t)\n"
    "cj = sum(1 for x in c if '\\u4e00'<=x<='\\u9fff')\n"
    "print('CJK_RATIO', cj/max(len(c),1))\n"
    "PYEOF",
    timeout=180,
)
print(o.read().decode())
print(e.read().decode())
c.close()