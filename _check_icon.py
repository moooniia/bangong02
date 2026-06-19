import paramiko, sys
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('139.196.28.78', username='root', password='OpenClaw2026')
# check icon in js and tabler version
stdin, out, err = ssh.exec_command("grep -n 'ti-file-upload\\|ti-refresh\\|再转' /home/toolbox/frontend/assets/tool-page.js && grep -r 'tabler' /home/toolbox/frontend/index.html | head -3")
data = out.read().decode('utf-8', errors='replace')
sys.stdout.buffer.write(data.encode('utf-8'))
ssh.close()
