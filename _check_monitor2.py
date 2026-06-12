#!/usr/bin/env python3
from ssh_helper import run

cmds = [
    "grep -n 'FAIL\\|Feishu notified' /home/toolbox/monitor.log | tail -20",
    "journalctl -u toolbox --since '2026-06-12 17:58' --until '2026-06-12 18:12' --no-pager | grep -E 'Stopping|Started|ocr|/api/ocr|health'",
    "ls -la /home/toolbox/fixtures/",
    "TOOLBOX_BASE=http://127.0.0.1:5000 /usr/bin/python3.8 /home/toolbox/monitor_check.py 2>&1 | tail -20",
]

for c in cmds:
    print("===", c[:90], "===")
    code, out, err = run(c, timeout=180)
    print(out or err or "(empty)")
    print()