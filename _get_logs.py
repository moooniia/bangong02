import paramiko, sys
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('139.196.28.78', username='root', password='OpenClaw2026')
stdin, out, err = ssh.exec_command('journalctl -u toolbox -n 60 --no-pager 2>&1')
data = out.read().decode('utf-8', errors='replace')
sys.stdout.buffer.write(data.encode('utf-8'))
ssh.close()
