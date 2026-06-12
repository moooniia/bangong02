#!/usr/bin/env python3
import re
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

for day in ("2026-06-11", "2026-06-12"):
    code, out, err = run(
        f"journalctl -u toolbox --since '{day} 00:00:00' --until '{day} 23:59:59' --no-pager 2>/dev/null",
        timeout=120,
    )
    lines = (out or "").splitlines()
    converts = [l for l in lines if "POST /api/convert" in l and " 200 " in l]
    physical = [l for l in lines if "PDF体检" in l]
    png_mode = [l for l in lines if "逐页 PNG" in l]
    volc_info = [l for l in lines if "volc_ocr" in l or "智能文档" in l]

    pages = []
    for l in physical:
        m = re.search(r"pages=(\d+)", l)
        if m:
            pages.append(int(m.group(1)))

    print(f"\n========== {day} ==========")
    print(f"POST /api/convert 成功: {len(converts)}")
    print(f"PDF体检(扫描件): {len(physical)}")
    print(f"逐页 PNG 日志: {len(png_mode)}")
    print(f"volc/智能文档 日志: {len(volc_info)}")
    if pages:
        print(f"扫描页数合计: {sum(pages)} (明细: {pages})")
        print(f"若每次扫描双通道计费: ~{sum(pages)*2} 页")

    for l in png_mode[:15]:
        print(" ", l[-120:])

# 本地 json 缓存里的 infer 日期（反映直接调 API 次数）
import os, glob
root = r"C:\Users\paz\toolbox-work"
jsons = glob.glob(os.path.join(root, "*detail*.json"))
print("\n========== 本地 OCR 缓存 JSON ==========")
for p in sorted(jsons):
    sz = os.path.getsize(p) // 1024
    print(os.path.basename(p), f"{sz}KB")

# 统计本地测试脚本数量
tests = glob.glob(os.path.join(root, "_*A*.py")) + glob.glob(os.path.join(root, "*1212*.py"))
print(f"\n本地 A/1212 相关测试脚本: {len(tests)} 个")