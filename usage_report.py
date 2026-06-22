"""查付费API调用次数：python usage_report.py [天数，默认30]"""
import json
import sys
import paramiko

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HOST = '139.196.28.78'
USER = 'root'
PASS = 'OpenClaw2026'

days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=15)
stdin, stdout, stderr = ssh.exec_command('cat /home/toolbox/backend/api_usage.json 2>/dev/null')
raw = stdout.read().decode()
ssh.close()

if not raw.strip():
    print('还没有任何付费API调用记录。')
    sys.exit(0)

data = json.loads(raw)
recent_dates = sorted(data.keys())[-days:]

NAMES = {
    'volc_word': 'PDF→Word(扫描件火山OCR)',
    'volc_excel': 'PDF→Excel(扫描件火山OCR)',
    'volc_ocr_text': '图片/PDF转文字(火山兜底)',
    'translate_text': '文本翻译',
    'translate_file': '文件翻译',
}

print(f'最近 {len(recent_dates)} 天每日明细：')
totals = {}
for d in recent_dates:
    day = data[d]
    parts = ', '.join(f'{NAMES.get(k, k)}={v}' for k, v in day.items())
    print(f'  {d}  {parts}')
    for k, v in day.items():
        totals[k] = totals.get(k, 0) + v

print('\n合计：')
for k, v in sorted(totals.items(), key=lambda x: -x[1]):
    print(f'  {NAMES.get(k, k)}: {v} 次')
