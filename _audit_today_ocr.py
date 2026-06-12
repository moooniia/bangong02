#!/usr/bin/env python3
"""统计今天智能文档解析相关调用（服务器日志）。"""
import re
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

TODAY = "2026-06-12"

code, out, err = run(
    f"journalctl -u toolbox --since '{TODAY} 00:00:00' --no-pager 2>/dev/null",
    timeout=120,
)
lines = (out or "").splitlines()
print(f"=== toolbox 日志行数 (since {TODAY}) ===")
print(len(lines))

patterns = {
    "pdf_convert_requests": r"POST /api/convert|convert.*docx|扫描件.*OCR",
    "volc_route_log": r"走火山 OCR|PDF体检.*走火山",
    "pdf_direct_ocr": r"pdf_to_markdown|PDF 直传",
    "image_mode_ocr": r"逐页 PNG|image_mode|图片模式",
    "volc_hybrid": r"volc-hybrid|detail 模式",
    "volc_fail": r"火山 OCR 失败|智能文档解析失败",
    "tier2": r"tier=2|tier= 2",
}

counts = {}
matched_lines = {k: [] for k in patterns}
for name, pat in patterns.items():
    rx = re.compile(pat)
    hits = [l for l in lines if rx.search(l)]
    counts[name] = len(hits)
    matched_lines[name] = hits[-8:]

for name, n in counts.items():
    print(f"{name}: {n}")

# 体检日志里提取页数
page_counts = []
for l in lines:
    m = re.search(r"PDF体检:.*pages=(\d+)", l)
    if m:
        page_counts.append(int(m.group(1)))
if page_counts:
    print(f"\nPDF体检记录: {len(page_counts)} 次, 页数合计 {sum(page_counts)}, 平均 {sum(page_counts)/len(page_counts):.1f}")

# 估算智能文档解析页数：每次扫描转换 ≈ 2×页数（直传+逐页PNG）
if page_counts:
    est_billed = sum(p * 2 for p in page_counts)
    print(f"估算智能文档解析计费页数(仅网站转换): ~{est_billed} 页")

print("\n=== 最近相关日志 ===")
for l in lines[-30:]:
    if any(k in l for k in ("PDF体检", "逐页 PNG", "走火山", "volc", "convert", "OCR")):
        print(l[:200])

# 查 /tmp 调试脚本
code2, out2, err2 = run(
    "find /tmp /home/toolbox -maxdepth 2 \\( -name '*.py' -o -name '*detail*.json' \\) -newermt '2026-06-12' 2>/dev/null | head -40",
    timeout=30,
)
print("\n=== 今天新建/修改的调试文件 ===")
print(out2 or err2 or "(无)")

# 历史对比
code3, out3, err3 = run(
    "journalctl -u toolbox --since '2026-06-11' --until '2026-06-12' --no-pager 2>/dev/null | grep -c 'PDF体检' || echo 0",
    timeout=60,
)
print("\n=== 昨天 PDF体检次数 ===")
print((out3 or err3).strip())