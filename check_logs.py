import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('139.196.28.78', username='root', password='OpenClaw2026', timeout=15)

_, out, _ = ssh.exec_command("journalctl -u toolbox -n 20 --no-pager 2>/dev/null")
sys.stdout.buffer.write(out.read())
print()
ssh.close()
