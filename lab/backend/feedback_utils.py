"""用户意见反馈 — 发到飞书（小美），同时落一份本地日志做备份。"""
import json
import os
import urllib.request
from datetime import datetime

ENV_PATH = os.environ.get('TOOLBOX_ENV', '/home/toolbox/toolbox.env')
_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feedback_log.txt')


def _load_env_file():
    if not os.path.isfile(ENV_PATH):
        return
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def _feishu_credentials():
    _load_env_file()
    return (
        os.environ.get('FEISHU_APP_ID', '').strip(),
        os.environ.get('FEISHU_APP_SECRET', '').strip(),
        os.environ.get('FEISHU_OPEN_ID', '').strip(),
    )


def _notify_feishu(text):
    app_id, app_secret, open_id = _feishu_credentials()
    if not app_id or not app_secret or not open_id:
        raise ValueError('飞书凭证未配置（toolbox.env 缺 FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_OPEN_ID）')
    token_req = urllib.request.Request(
        'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
        data=json.dumps({'app_id': app_id, 'app_secret': app_secret}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(token_req, timeout=15) as r:
        token = json.loads(r.read().decode()).get('tenant_access_token', '')
    if not token:
        return False
    msg_req = urllib.request.Request(
        'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
        data=json.dumps({
            'receive_id': open_id,
            'msg_type': 'text',
            'content': json.dumps({'text': text}),
        }).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(msg_req, timeout=15) as r:
        resp = json.loads(r.read().decode())
    return resp.get('code', -1) == 0


def submit_feedback(message, contact=''):
    """发飞书通知 + 本地落盘备份；飞书发送失败也不影响本地记录成功。"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {message}' + (f'  (联系方式: {contact})' if contact else '')
    try:
        with open(_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

    text = f'【办公工具箱·意见反馈】\n{message}'
    if contact:
        text += f'\n联系方式：{contact}'
    try:
        ok = _notify_feishu(text)
        print(f'[反馈] 飞书推送{"成功" if ok else "失败(返回非0 code)"}', flush=True)
    except Exception as e:
        print(f'[反馈] 飞书推送异常: {e}', flush=True)
