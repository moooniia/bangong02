#!/usr/bin/env python3
import re
import zipfile

path = r"C:\Users\paz\Desktop\P T W 测试\page_1_p2_v096.docx"
with zipfile.ZipFile(path) as z:
    xml = z.read("word/document.xml").decode("utf-8")
    rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    imgs = [x for x in rels.splitlines() if "image" in x]
    print("image rels", len(imgs))
    names = re.findall(r'name="(FloatImg\d+)"', xml)
    print("float names", names)