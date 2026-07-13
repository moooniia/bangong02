import glob
import os
import paramiko

HOST = '139.196.28.78'
USER = 'root'
PASS = 'OpenClaw2026'
LOCAL_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server', 'frontend')
REMOTE_DIR = '/home/toolbox/frontend'

# 自动收集所有前端文件，不再手动维护清单（之前漏掉过 image-to-text.html /
# scan-to-text.html / image-rotate.html，靠手写清单太容易漏文件）
files_to_deploy = sorted(
    os.path.relpath(p, LOCAL_DIR).replace(os.sep, '/')
    for pattern in ('*.html', '*.json', 'assets/*', 'downloads/*')
    for p in glob.glob(os.path.join(LOCAL_DIR, pattern))
    if os.path.isfile(p)
)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=15)
sftp = ssh.open_sftp()

for f in files_to_deploy:
    local  = os.path.join(LOCAL_DIR, f)
    remote = f'{REMOTE_DIR}/{f}'
    remote_dir = os.path.dirname(remote)
    if remote_dir and remote_dir != REMOTE_DIR:
        parts = remote_dir.replace(REMOTE_DIR, '').strip('/').split('/')
        current = REMOTE_DIR
        for part in parts:
            current = f'{current}/{part}'
            try:
                sftp.mkdir(current)
            except OSError:
                pass
    sftp.put(local, remote)
    print(f'Uploaded: {f}')

sftp.close()

_, out, _ = ssh.exec_command(f'ls -lh {REMOTE_DIR}/index.html {REMOTE_DIR}/pdf-editor.html')
print(out.read().decode().strip())

ssh.close()
print('Done.')
