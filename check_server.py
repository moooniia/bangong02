import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('139.196.28.78', username='root', password='OpenClaw2026', timeout=15)

_, out, _ = ssh.exec_command("grep -n '个工具' /home/toolbox/frontend/index.html")
print(out.read().decode())

_, out, _ = ssh.exec_command("grep -c 'pdf-searchable' /home/toolbox/frontend/index.html")
print('pdf-searchable occurrences:', out.read().decode().strip())

ssh.close()
