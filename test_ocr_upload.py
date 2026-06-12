#!/usr/bin/env python3
import os
import paramiko

HOST, USER, PW = "139.196.28.78", "root", "OpenClaw2026"
local = r"C:\Users\paz\Desktop\测试题\职工之家  金伯玉.jpg"
remote = "/tmp/test_ocr.jpg"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PW, timeout=30)
sftp = c.open_sftp()
sftp.put(local, remote)
sftp.close()

script = f"""
python3.8 << 'PYEOF'
import cv2, numpy as np, pytesseract, re
from PIL import Image

path = '{remote}'

def old_ocr(p):
    return pytesseract.image_to_string(Image.open(p), lang='chi_sim+eng').strip()

def preprocess(p):
    img = cv2.imread(p)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h,w = gray.shape
    if max(h,w) < 1800:
        s = 1800/max(h,w)
        gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    gray = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    return cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,35,11)

def clean(t):
    t = re.sub(r'(?<=[\u4e00-\u9fff])\\s+(?=[\u4e00-\u9fff])', '', t)
    return re.sub(r'\\n{{3,}}', '\\n\\n', t).strip()

def new_ocr(p):
    proc = preprocess(p)
    cfg = '--psm 6 --oem 1'
    t = pytesseract.image_to_string(Image.fromarray(proc), lang='chi_sim', config=cfg)
    return clean(t)

print('OLD:', old_ocr(path)[:300])
print('---')
print('NEW:', new_ocr(path)[:300])
PYEOF
"""
_, o, e = c.exec_command(script, timeout=60)
print(o.read().decode())
print(e.read().decode())
c.close()