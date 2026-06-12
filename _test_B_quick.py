import requests

PDF = r"C:\Users\paz\Desktop\P T W 测试\B.pdf"
with open(PDF, "rb") as f:
    r = requests.post(
        "http://139.196.28.78/api/convert",
        files={"file": ("B.pdf", f, "application/pdf")},
        data={"format": "docx"},
        timeout=300,
    )
print(r.json())