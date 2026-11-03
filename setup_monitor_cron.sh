#!/bin/bash
# 在服务器上执行：安装巡检 cron（每 6 小时 + 每日 9 点简报）
set -e
chmod +x /home/toolbox/monitor_check.py
CHECK_LINE='0 */6 * * * TOOLBOX_BASE=http://127.0.0.1:5000 /usr/bin/python3.8 /home/toolbox/monitor_check.py >> /home/toolbox/monitor.log 2>&1'
BRIEF_LINE='0 9 * * * TOOLBOX_BASE=http://127.0.0.1:5000 /usr/bin/python3.8 /home/toolbox/monitor_check.py --briefing >> /home/toolbox/monitor.log 2>&1'
( crontab -l 2>/dev/null | grep -v monitor_check.py || true
  echo "$CHECK_LINE"
  echo "$BRIEF_LINE"
) | crontab -
echo "Cron installed:"
crontab -l | grep monitor_check || true