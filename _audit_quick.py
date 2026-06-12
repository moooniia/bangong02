import sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

for label, cmd in [
    ("convert_today", "journalctl -u toolbox --since '2026-06-12 00:00:00' --no-pager | grep -c 'POST /api/convert'"),
    ("tier2_today", "journalctl -u toolbox --since '2026-06-12 00:00:00' --no-pager | grep 'tier=2' | wc -l"),
    ("volc_start_today", "journalctl -u toolbox --since '2026-06-12 00:00:00' --no-pager | grep -c '走火山 OCR 智能文档解析'"),
    ("volc_start_yesterday", "journalctl -u toolbox --since '2026-06-11' --until '2026-06-12' --no-pager | grep -c '走火山 OCR 智能文档解析'"),
    ("convert_yesterday", "journalctl -u toolbox --since '2026-06-11' --until '2026-06-12' --no-pager | grep -c 'POST /api/convert'"),
]:
    _, out, err = run(cmd, timeout=60)
    print(label, (out or err).strip())