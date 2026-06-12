import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))
from ssh_helper import run

cmd = r"""
cd /home/toolbox && TOOLBOX_ENV=/home/toolbox/toolbox.env python3.8 - <<'PYEOF'
import re, sys
sys.path.insert(0,"/home/toolbox/backend")
from volc_ocr import pdf_to_markdown_image_mode
pages = pdf_to_markdown_image_mode("/tmp/B.pdf")
print("pages", len(pages))
for i, md in enumerate(pages):
    print("--- page", i, "len", len(md))
    for ln in md.split("\n")[:20]:
        print(repr(ln[:140]))
PYEOF
"""
_, out, err = run(cmd, timeout=180)
print(out or err)