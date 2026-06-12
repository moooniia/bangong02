#!/usr/bin/env python3
import paramiko

HOST, USER, PW = "139.196.28.78", "root", "OpenClaw2026"
local = r"C:\Users\paz\Desktop\1.pdf"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PW, timeout=30)
sftp = c.open_sftp()
sftp.put(local, "/tmp/1.pdf")
sftp.close()

script = r"""
echo '=== file ==='
file /tmp/1.pdf
ls -la /tmp/1.pdf
echo '=== pdftotext len ==='
pdftotext /tmp/1.pdf - 2>&1 | wc -c
pdftotext /tmp/1.pdf - 2>&1 | head -5
echo '=== libreoffice direct ==='
cp /tmp/1.pdf /tmp/test_conv.pdf
libreoffice --headless --convert-to docx:'MS Word 2007 XML' --outdir /tmp /tmp/test_conv.pdf 2>&1
ls -la /tmp/*.docx 2>/dev/null | tail -3
echo '=== python route ==='
python3.8 << 'PYEOF'
import sys
sys.path.insert(0,'/home/toolbox/backend')
from app import pdf_has_text, convert_scanned_pdf_to_docx, ocr_pdf
import os, uuid
print('has_text', pdf_has_text('/tmp/1.pdf'))
uid = str(uuid.uuid4())
try:
    if pdf_has_text('/tmp/1.pdf'):
        import subprocess
        subprocess.run(['libreoffice','--headless','--convert-to','docx:MS Word 2007 XML','--outdir','/tmp','/tmp/1.pdf'],capture_output=True,text=True,timeout=120)
        print('lo files', [f for f in os.listdir('/tmp') if f.endswith('.docx')])
    else:
        convert_scanned_pdf_to_docx('/tmp/1.pdf', uid, '/tmp')
        print('ocr docx', [f for f in os.listdir('/tmp') if f.endswith('.docx')])
except Exception as e:
    import traceback
    traceback.print_exc()
PYEOF
"""
_, o, e = c.exec_command(script, timeout=300)
print(o.read().decode())
print(e.read().decode())
c.close()