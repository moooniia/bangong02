import sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

cmds = [
    "pdfinfo /home/toolbox/fixtures/2.pdf 2>/dev/null | grep Pages || echo 'no 2.pdf'",
    "grep -c '走火山 OCR' /home/toolbox/monitor.log 2>/dev/null || echo 0",
    "journalctl -u toolbox --since '2026-06-10' --no-pager 2>/dev/null | grep -c '走火山 OCR' || echo 0",
    "journalctl -u toolbox --since '2026-06-10' --no-pager 2>/dev/null | grep -c '火山 OCR 失败' || echo 0",
    "journalctl -u toolbox --since '2026-06-10' --no-pager 2>/dev/null | grep '走火山 OCR' | tail -20",
]
for c in cmds:
    print("===", c[:60], "===")
    code, out, err = run(c, timeout=30)
    print(out or err)