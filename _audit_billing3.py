#!/usr/bin/env python3
import re, sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

for day in ("2026-06-11", "2026-06-12"):
    code, out, err = run(
        f"journalctl -u toolbox --since '{day} 00:00:00' --until '{day} 23:59:59' --no-pager",
        timeout=120,
    )
    lines = (out or "").splitlines()
    keys = [
        "POST /api/convert",
        "PDF体检",
        "Stage2: 火山",
        "火山 OCR 完成",
        "直接使用火山 OCR",
        "逐页 PNG",
        "扫描件：两阶段",
        "tier=0",
        "tier=1",
        "tier=2",
    ]
    print(f"\n=== {day} ===")
    for k in keys:
        n = sum(1 for l in lines if k in l)
        print(f"  {k}: {n}")

    # 提取每次火山完成时的 route（估算真实转换次数）
    routes = re.findall(r"火山 OCR 完成 route=(\S+)", "\n".join(lines))
    if routes:
        from collections import Counter
        print(f"  火山完成次数: {len(routes)}", dict(Counter(routes)))

    # 每次体检的页数
    exams = []
    for l in lines:
        if "PDF体检" in l and "tier=" in l:
            m = re.search(r"tier=(\d+).*pages=(\d+)", l)
            if m:
                exams.append((int(m.group(1)), int(m.group(2))))
    if exams:
        print(f"  体检记录(去重前半): {exams[::2]}")

# 估算昨天总量能否到 512+36
print("\n=== 账单对照 ===")
print("昨天控制台: 免费512 + 付费32~36 ≈ 544~548 次")
print("今天控制台: 付费 224 次")
print()
print("计费规则(我们代码): 每份扫描件 ≈ 2×页数 (PDF直传N + 逐页PNG N)")
print()
scenarios = [
    ("昨天网站17次旧日志×12页×2", 17*12*2),
    ("昨天网站17次旧日志×7页×2", 17*7*2),
    ("今天00点1212脚本3次×12页(仅直传)", 3*12),
    ("今天00点1212脚本3次×12页×2(全流程)", 3*12*2),
    ("今天A验收1次×7页×2", 14),
    ("今天B验收1次×3页×2", 6),
    ("今天C验收1次×1页(至少直传1次)", 1),
]
for name, v in scenarios:
    print(f"  {name} = {v}")