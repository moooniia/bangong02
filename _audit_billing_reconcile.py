#!/usr/bin/env python3
"""对照火山控制台：估算智能文档解析计费次数。"""
import glob
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

# 计费模型（与 volc_ocr.py 一致）
# 扫描件 volc_pdf_to_docx:
#   1) pdf_to_markdown: 按 PDF 页数 N 计费（chunk 一次但 page_num=N）
#   2) 需 image_mode 时 pdf_to_detail/markdown_image_mode: 再 N 次（逐页 PNG）
# => 典型扫描合同约 2N 次/份


def pages_from_tier2_line(line):
    m = re.search(r"pages=(\d+)", line)
    return int(m.group(1)) if m else 0


def estimate_billed_pages(n_pages, double_pass=True):
    if n_pages <= 0:
        return 0
    return n_pages * 2 if double_pass else n_pages


for day, free_hint, paid_hint in (
    ("2026-06-11", 512, "32-36"),
    ("2026-06-12", 0, 224),
):
    code, out, err = run(
        f"journalctl -u toolbox --since '{day} 00:00:00' --until '{day} 23:59:59' --no-pager",
        timeout=120,
    )
    lines = (out or "").splitlines()

    converts = [l for l in lines if "POST /api/convert" in l and " 200 " in l]
    tier2 = [l for l in lines if "tier=2" in l and "PDF体检" in l]
    tier0 = [l for l in lines if "tier=0" in l and "PDF体检" in l]
    tier1 = [l for l in lines if "tier=1" in l and "PDF体检" in l]
    old_volc = [l for l in lines if "走火山 OCR 智能文档解析" in l]

    tier2_pages = [pages_from_tier2_line(l) for l in tier2]
    # 旧日志每条打两行
    old_volc_n = len(old_volc) // 2

    site_est = sum(estimate_billed_pages(p) for p in tier2_pages)

    print(f"\n{'='*60}")
    print(f"{day}  控制台: 免费≈{free_hint}  付费≈{paid_hint}")
    print(f"{'='*60}")
    print(f"网站 convert 成功: {len(converts)}")
    print(f"PDF体检 tier=0 本地: {len(tier0)//2}")
    print(f"PDF体检 tier=1 Tesseract: {len(tier1)//2}")
    print(f"PDF体检 tier=2 火山: {len(tier2)//2}  页数明细: {tier2_pages}")
    print(f"旧版日志「走火山智能文档解析」: {old_volc_n} 次转换")
    print(f"网站 tier=2 估算智能文档计费: ~{site_est} 次")

    if old_volc_n and not tier2_pages:
        # 6/11 无 PDF体检，用旧日志次数 × 典型页数估算
        for avg_pages, label in ((12, "1212/长合同"), (7, "A 7页"), (3, "B 3页")):
            est = old_volc_n * estimate_billed_pages(avg_pages)
            print(f"  若旧日志每次均为 {label}: ~{est} 次")

# 服务器直跑脚本（不计入 convert）
code2, out2, err2 = run(
    "ls -la /tmp/1212*.json /home/toolbox/1212*.json 2>/dev/null; "
    "stat -c '%y %n' /tmp/1212*.json /home/toolbox/1212*.json 2>/dev/null",
    timeout=30,
)
print(f"\n{'='*60}")
print("服务器 1212 OCR 缓存（直跑脚本，额外计费）")
print((out2 or err2 or "").strip() or "(无)")

# 本地直跑脚本统计
root = r"C:\Users\paz\toolbox-work"
scripts = []
for pat in ("*1212*.py", "_probe*.py", "_test_A*.py", "_test_B*.py", "run_*.py", "analyze_1212*.py"):
    scripts.extend(glob.glob(os.path.join(root, pat)))
scripts = sorted(set(scripts))
print(f"\n本地可能直连接口/服务器的 OCR 脚本: {len(scripts)} 个")

# 本地 json 时间
print("\n本地 1212 detail 缓存:")
for p in sorted(glob.glob(os.path.join(root, "*detail*.json"))):
    print(f"  {os.path.basename(p)}  {os.path.getsize(p)//1024}KB  mtime={os.path.getmtime(p):.0f}")

print("\n--- 结论提示 ---")
print("付费 224（今天）若全是扫描件：约等于 16 份 7 页合同(×14) 或 9 份 12 页(×24)")
print("免费 512（昨天）+ 付费 32-36：说明昨天先用完免费额度，后续约 2-3 份长文档转付费")