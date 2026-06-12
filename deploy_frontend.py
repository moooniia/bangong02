import paramiko
import os

HOST = '139.196.28.78'
USER = 'root'
PASS = 'OpenClaw2026'
LOCAL_DIR = r'C:\Users\paz\toolbox-work'
REMOTE_DIR = '/home/toolbox/frontend'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=15)

sftp = ssh.open_sftp()

files_to_deploy = ['pdf-searchable.html', 'index.html']
for f in files_to_deploy:
    local = os.path.join(LOCAL_DIR, f)
    remote = f'{REMOTE_DIR}/{f}'
    sftp.put(local, remote)
    print(f'Uploaded: {f}')

sftp.close()

# Verify
_, out, _ = ssh.exec_command(f'ls -lh {REMOTE_DIR}/pdf-searchable.html {REMOTE_DIR}/index.html')
print(out.read().decode().strip())

ssh.close()
print('Done.')
