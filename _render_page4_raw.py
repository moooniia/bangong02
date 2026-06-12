#!/usr/bin/env python3
import fitz
import os

PDF = r"C:\Users\paz\Desktop\P T W 测试\page_4.pdf"
OUT = r"C:\Users\paz\Desktop\P T W 测试\page_4_raw_render.png"

doc = fitz.open(PDF)
page = doc[0]
for dpi in (72, 150):
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    path = OUT.replace(".png", f"_{dpi}dpi.png")
    pix.save(path)
    print(path, pix.width, pix.height, "rot=", page.rotation)
doc.close()