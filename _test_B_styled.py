import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ssh_helper import fetch, run

PDF = r"C:\Users\paz\Desktop\P T W 测试\B.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\B_site_styled.docx"

run(f"cp '{PDF.replace(chr(92), '/')}' /tmp/B.pdf 2>/dev/null || true", timeout=30)
# upload via sftp
from ssh_helper import put

put(PDF, "/tmp/B.pdf")

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import volc_pdf_to_docx
info = volc_pdf_to_docx("/tmp/B.pdf", "/tmp/B_styled.docx")
print(info)
PYEOF
"""
_, out, err = run(cmd, timeout=300)
print(out or err)
fetch("/tmp/B_styled.docx", OUT)
print("saved", OUT)