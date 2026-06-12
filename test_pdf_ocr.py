import requests
import os

BASE = 'http://139.196.28.78:5000'
PDF = r'C:\Users\paz\Desktop\1212\1212.pdf'

print('Testing pdf_ocr endpoint...')
with open(PDF, 'rb') as f:
    r = requests.post(f'{BASE}/api/convert',
                      files={'file': ('1212.pdf', f, 'application/pdf')},
                      data={'format': 'pdf_ocr'},
                      timeout=300,
                      proxies={'http': None, 'https': None})

print('Status:', r.status_code)
data = r.json()
print('Response:', data)

if data.get('success'):
    filename = data['filename']
    display = data.get('display_name', filename)
    print(f'display_name: {display}')

    # Download
    dl = requests.get(f'{BASE}/api/download/{filename}', timeout=30,
                      proxies={'http': None, 'https': None})
    print(f'Download status: {dl.status_code}, size: {len(dl.content)/1024:.1f} KB')

    out = os.path.join(r'C:\Users\paz\Desktop\1212', display)
    with open(out, 'wb') as f:
        f.write(dl.content)
    print(f'Saved to: {out}')
