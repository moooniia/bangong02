#!/usr/bin/env python3
import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('139.196.28.78', username='root', password='OpenClaw2026', timeout=30)
script = r"""
libreoffice --headless --convert-to 'docx:MS Word 2007 XML' --outdir /home/toolbox/outputs /tmp/1.pdf 2>&1
ls -la /home/toolbox/outputs/1.docx 2>&1 || echo 'no 1.docx'
python3.8 << 'PYEOF'
import subprocess, os
from docx import Document
r = subprocess.run(['pdftotext', '/tmp/1.pdf', '-'], capture_output=True, text=True, timeout=60)
d = Document()
for line in r.stdout.split('\n'):
    p = line.strip()
    if p:
        d.add_paragraph(p)
out = '/home/toolbox/outputs/fallback_test.docx'
d.save(out)
print('fallback ok', os.path.getsize(out), 'chars', len(r.stdout))
PYEOF
"""
_, o, e = c.exec_command(script, timeout=120)
print(o.read().decode())
print(e.read().decode())
c.close()