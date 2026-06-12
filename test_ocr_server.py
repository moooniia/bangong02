#!/usr/bin/env python3
import paramiko

script = r"""
which pdftoppm
pdftoppm -v 2>&1 | head -1

python3.8 << 'PYEOF'
import cv2, numpy as np, pytesseract, re, os, tempfile
from PIL import Image

def preprocess(path):
    img = cv2.imread(path)
    if img is None:
        pil = Image.open(path)
        img = cv2.cvtColor(np.array(pil.convert('RGB')), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if max(h, w) < 1800:
        s = 1800 / max(h, w)
        gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    gray = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11)

def clean(text):
    text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def ocr(path, psm=6, lang='chi_sim'):
    proc = preprocess(path)
    cfg = f'--psm {psm} --oem 1'
    return clean(pytesseract.image_to_string(Image.fromarray(proc), lang=lang, config=cfg))

# test on a generated chinese image if no sample
from PIL import Image, ImageDraw, ImageFont
p = '/tmp/ocr_test.png'
img = Image.new('RGB', (800, 200), 'white')
d = ImageDraw.Draw(img)
d.text((20, 80), '6月9日国务院发布重要政策，国内经济稳步发展。', fill='black')
img.save(p)
for psm in [3, 6, 11]:
    print('PSM', psm, ':', ocr(p, psm)[:80])
PYEOF
"""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('139.196.28.78', username='root', password='OpenClaw2026', timeout=30)
_, o, e = c.exec_command(script, timeout=120)
print(o.read().decode())
print(e.read().decode())
c.close()