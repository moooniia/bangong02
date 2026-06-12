import requests
import os

BASE = 'http://139.196.28.78:5000'
PDF = r'C:\Users\paz\Desktop\1212\1212.pdf'
proxies = {'http': None, 'https': None}

print('Testing PDF to docx (should now use Volc OCR for 1212.pdf)...')
with open(PDF, 'rb') as f:
    r = requests.post(f'{BASE}/api/convert',
                      files={'file': ('1212.pdf', f, 'application/pdf')},
                      data={'format': 'docx'},
                      timeout=300,
                      proxies=proxies)

print('Status:', r.status_code)
data = r.json()
print('Success:', data.get('success'))
if not data.get('success'):
    print('Error:', data.get('error'))
else:
    filename = data['filename']
    dl = requests.get(f'{BASE}/api/download/{filename}', timeout=30, proxies=proxies)
    size_kb = len(dl.content) / 1024
    print(f'File size: {size_kb:.1f} KB')

    out = rf'C:\Users\paz\Desktop\1212\1212_new_v4.docx'
    with open(out, 'wb') as f:
        f.write(dl.content)
    print(f'Saved: {out}')

    if size_kb > 200:
        print('OK - large file, likely has embedded images (Volc OCR used)')
    elif size_kb > 40:
        print('MEDIUM - some content but possibly Tesseract only')
    else:
        print('SMALL - likely Tesseract only, fix may not have worked')
