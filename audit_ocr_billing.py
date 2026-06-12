#!/usr/bin/env python3
"""估算一次调试周期会打几次火山 OCR（解释为何页数烧得快）。"""
import sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

# 服务器日志：每次「走火山 OCR」= 1 次 pdf_to_markdown = 按 PDF 页数扣费
code, out, err = run(
    "journalctl -u toolbox --since '2026-06-11' --no-pager | grep 'INFO in app' | grep -E '走火山 OCR|扫描件，OCR'",
    timeout=30,
)
lines = [l for l in (out or "").splitlines() if l.strip()]
print("=== 网站 API 触发的 OCR 次数 ===")
print(len([l for l in lines if "走火山 OCR" in l]))

# 典型调试动作（每次1212.pdf=12页）
actions = [
    ("deploy 冒烟 pdf->word (2.pdf 3页)", 3),
    ("convert 1212.pdf 一次", 12),
    ("analyze_1212 拉明细（不走app日志）", 12),
    ("diag_1212_remote 诊断", 12),
    ("verify_page1 / benchmark 各一次", 12),
]
print("\n=== 单轮若全做，1212 相关页数 ===")
for name, pages in actions[1:]:
    print(f"  {name}: {pages} 页")
print("  一轮合计(含convert+analyze): 24~36 页")
print("  10轮类似调试: 240~360 页")
print("  20轮: 480~720 页 → 可耗尽500页免费额度")