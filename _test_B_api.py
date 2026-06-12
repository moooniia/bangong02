import os
import requests

PDF = r"C:\Users\paz\Desktop\P T W 测试\B.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\B_web.docx"
URL = "http://139.196.28.78/api/convert"

with open(PDF, "rb") as f:
    r = requests.post(URL, files={"file": ("B.pdf", f, "application/pdf")}, data={"format": "docx"}, timeout=300)

print("status", r.status_code)
try:
    data = r.json()
    print("json", data)
except Exception:
    print(r.text[:500])
    raise SystemExit(1)

if not data.get("success"):
    raise SystemExit(1)

# download result
dl = requests.get(f"http://139.196.28.78/api/download/{data['filename']}", timeout=120)
dl.raise_for_status()
with open(OUT, "wb") as f:
    f.write(dl.content)
print("saved", OUT, "bytes", len(dl.content))