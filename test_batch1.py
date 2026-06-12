#!/usr/bin/env python3
import urllib.request

BASE = "http://139.196.28.78"
pages = [
    "/pdf-merge.html", "/pdf-split.html", "/pdf-rotate.html", "/pdf-compress.html",
    "/pdf-to-image.html", "/images-to-pdf.html", "/image-compress.html",
    "/image-resize.html", "/image-convert.html", "/qrcode.html",
]
for p in pages:
    with urllib.request.urlopen(BASE + p, timeout=10) as r:
        print(p, r.status)