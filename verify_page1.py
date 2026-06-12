#!/usr/bin/env python3
"""第 1 页自动验收：对照 1212.pdf 与输出 docx，检查字体/版式/元素。"""
import io
import json
import os
import re
import sys
import tempfile
import urllib.request
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server", "backend"))

PDF = r"C:\Users\paz\Desktop\1212.pdf"
REF = r"C:\Users\paz\Desktop\2024中国移动长三角G5生态谷数据中心一期土建工程基坑监测项目服务合同 29.74254.docx"
API = "http://139.196.28.78/api/convert"


def convert_1212(out_docx):
    boundary = "----VerifyP1"
    with open(PDF, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="1212.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="format"\r\n\r\n'
        f"docx\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode())
    url = f"http://139.196.28.78/api/download/{resp['filename']}"
    urllib.request.urlretrieve(url, out_docx)
    return out_docx


def page1_paragraphs(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        doc = z.read("word/document.xml").decode("utf-8", errors="replace")
    p1 = doc.split('w:br w:type="page"')[0]
    items = []
    for p in re.findall(r"<w:p[ >][\s\S]*?</w:p>", p1):
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)
        text = "".join(texts).strip()
        if not text and "<pic:pic" not in p:
            continue
        jc = re.search(r'w:jc w:val="(\w+)"', p)
        sb = re.search(r'w:before="(\d+)"', p)
        runs = []
        for r in re.findall(r"<w:r[\s\S]*?</w:r>", p):
            t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r)).strip()
            if not t and "<pic:pic" not in r:
                continue
            color = re.search(r'w:color w:val="([^"]+)"', r)
            font = re.search(r'w:eastAsia="([^"]+)"', r)
            sz = re.search(r'w:sz w:val="(\d+)"', r)
            runs.append({
                "text": t[:60],
                "color": color.group(1) if color else None,
                "font": font.group(1) if font else None,
                "sz_half": int(sz.group(1)) if sz else None,
                "has_pic": "<pic:pic" in r,
            })
        items.append({
            "text": text[:80],
            "align": jc.group(1) if jc else "left",
            "space_before_twips": int(sb.group(1)) if sb else 0,
            "pics": p.count("<pic:pic"),
            "runs": runs,
        })
    return items, p1.count("<pic:pic")


def pdf_page1_ocr_expect():
    import fitz
    doc = fitz.open(PDF)
    page = doc[0]
    return {
        "size": (page.rect.width, page.rect.height),
        "text_snips": page.get_text()[:500],
    }


def check(docx_path):
    paras, pics = page1_paragraphs(docx_path)
    issues = []
    ok = []

    texts = [p["text"] for p in paras if p["text"]]
    all_text = "\n".join(texts)

    if re.search(r"332024\d+", all_text):
        blue = any(
            r.get("color") == "008FEF"
            for p in paras for r in p["runs"] if "332024" in r.get("text", "")
        )
        if blue:
            ok.append("蓝色盖章编号")
        else:
            issues.append("盖章编号缺蓝色")
    else:
        issues.append("缺盖章编号")

    if "CMCCTD-SS-202400146" in all_text:
        ok.append("合同编号")
    else:
        issues.append("缺合同编号")

    if "服务合同" in all_text:
        hei = any(
            r.get("font") == "SimHei" and (r.get("sz_half") or 0) >= 40
            for p in paras for r in p["runs"] if "服务合同" in r.get("text", "")
        )
        if hei:
            ok.append("服务合同黑体大字")
        else:
            issues.append("服务合同字体/字号不对")
    else:
        issues.append("缺「服务合同」")

    if re.search(r"甲方.*【.*】", all_text) and re.search(r"乙方.*【.*】", all_text):
        ok.append("甲乙方格式")
    else:
        issues.append("甲乙方格式不全")

    if "5G生态" in all_text or "G5生态" in all_text:
        ok.append("项目名称")
    else:
        issues.append("项目名称异常")

    if pics >= 2:
        ok.append(f"嵌入图 {pics} 个(章/二维码)")
    else:
        issues.append(f"图太少({pics})，可能缺二维码或章图")

    if not re.search(r"臻子|至善|德厚|李于", all_text):
        ok.append("水印文字已滤除")
    else:
        issues.append("仍有水印碎片")

    # 版式：服务合同应居中，甲乙方左对齐
    for p in paras:
        if "服务合同" in p["text"] and p["align"] != "center":
            issues.append("服务合同未居中")
        if p["text"].startswith("甲方") and p["align"] not in ("left", "both"):
            issues.append("甲方未左对齐")

    return {"ok": ok, "issues": issues, "paras": paras, "pics": pics}


def main():
    out = os.path.join(tempfile.gettempdir(), "1212_verify_p1.docx")
    print("converting...")
    convert_1212(out)
    print("checking", out)
    r = check(out)
    print("\n=== OK ===")
    for x in r["ok"]:
        print(" ", x)
    print("\n=== ISSUES ===")
    for x in r["issues"]:
        print(" ", x)
    print("\n=== PARAS ===")
    for i, p in enumerate(r["paras"], 1):
        print(f"{i}. [{p['align']}] pics={p['pics']} | {p['text'][:60]}")
        for run in p["runs"]:
            if run["has_pic"]:
                print("   [IMAGE]")
            else:
                print(f"   {run['text'][:40]} font={run['font']} sz={run['sz_half']} color={run['color']}")
    if os.path.isfile(REF):
        rr = check(REF)
        print("\n=== REF ISSUES (page1) ===", len(rr["issues"]))
    return 0 if not r["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())