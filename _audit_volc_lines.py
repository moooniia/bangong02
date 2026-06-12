#!/usr/bin/env python3
import sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

for day in ("2026-06-11", "2026-06-12"):
    code, out, err = run(
        f"journalctl -u toolbox --since '{day} 00:00:00' --until '{day} 23:59:59' --no-pager "
        f"| grep -E 'volc|智能文档|逐页|走火山|PDF体检|tier='",
        timeout=90,
    )
    lines = [l for l in (out or "").splitlines() if l.strip()]
    print(f"=== {day} hits {len(lines)} ===")
    for l in lines[:30]:
        print(l[-170:])
    if len(lines) > 30:
        print("...", len(lines) - 30, "more")