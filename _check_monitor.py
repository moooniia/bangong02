#!/usr/bin/env python3
from ssh_helper import run

cmds = [
    "date",
    "crontab -l 2>/dev/null | grep -i monitor",
    "grep '2026-06-12 18:' /home/toolbox/monitor.log 2>/dev/null",
    "grep '2026-06-12 17:' /home/toolbox/monitor.log 2>/dev/null",
    "tail -150 /home/toolbox/monitor.log 2>/dev/null",
    "systemctl is-active toolbox",
    "curl -s http://127.0.0.1:5000/api/health",
    "journalctl -u toolbox --since '2026-06-12 17:50' --until '2026-06-12 18:20' --no-pager 2>/dev/null | tail -60",
]

for c in cmds:
    print("===", c[:80], "===")
    code, out, err = run(c, timeout=90)
    print(out or err or "(empty)")
    print()