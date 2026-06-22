"""查意见反馈记录：python feedback_report.py"""
import sys
import paramiko

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HOST = '139.196.28.78'
USER = 'root'
PASS = 'OpenClaw2026'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=15)
stdin, stdout, stderr = ssh.exec_command('cat /home/toolbox/backend/feedback_log.txt 2>/dev/null')
raw = stdout.read().decode('utf-8')
ssh.close()

if not raw.strip():
    print('还没有任何反馈记录。')
    sys.exit(0)

lines = [l for l in raw.splitlines() if l.strip()]
print(f'共 {len(lines)} 条反馈：\n')
for l in lines:
    print(l)
