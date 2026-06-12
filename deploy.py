#!/usr/bin/env python3
"""Deploy toolbox project to server."""
import glob
import os
import paramiko

HOST = "139.196.28.78"
USER = "root"
PASSWORD = "OpenClaw2026"
LOCAL_BASE = os.path.join(os.path.dirname(__file__), "server")
REMOTE_BASE = "/home/toolbox"


def collect_files():
    files = ["toolbox.service"]
    for py in glob.glob(os.path.join(LOCAL_BASE, "backend", "*.py")):
        files.append("backend/" + os.path.basename(py))
    for pattern in ["frontend/*.html", "frontend/assets/*"]:
        for f in glob.glob(os.path.join(LOCAL_BASE, pattern.replace("/", os.sep))):
            rel = os.path.relpath(f, LOCAL_BASE).replace("\\", "/")
            files.append(rel)
    return sorted(set(files))


MONITOR_FILES = [
    "monitor_check.py",
    "monitor.env.example",
    "toolbox.env.example",
    "setup_monitor_cron.sh",
    "setup_umami.sh",
    "umami_init.py",
]
UMAMI_FILES = ["umami/docker-compose.yml"]
FIXTURE_UPLOADS = [
    (os.path.join(os.path.expanduser("~"), "Desktop", "2.pdf"), "fixtures/2.pdf"),
    (os.path.join(os.path.expanduser("~"), "Desktop", "1.png"), "fixtures/1.png"),
]


def collect_deploy_files():
    files = collect_files()
    base = os.path.dirname(__file__)
    for name in MONITOR_FILES:
        local = os.path.join(base, name)
        if os.path.isfile(local):
            files.append(name)
    for name in UMAMI_FILES:
        local = os.path.join(base, name)
        if os.path.isfile(local):
            files.append(name)
    return sorted(set(files))


FILES = collect_deploy_files()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
sftp = client.open_sftp()

PROJECT_BASE = os.path.dirname(__file__)

for rel in FILES:
    if rel in MONITOR_FILES or rel in UMAMI_FILES:
        local = os.path.join(PROJECT_BASE, rel.replace("/", os.sep))
    else:
        local = os.path.join(LOCAL_BASE, rel.replace("/", os.sep))
    if not os.path.isfile(local):
        continue
    if rel.endswith(".service"):
        remote = f"/etc/systemd/system/{os.path.basename(rel)}"
    elif rel in MONITOR_FILES:
        remote = f"{REMOTE_BASE}/{os.path.basename(rel)}"
    elif rel in UMAMI_FILES:
        remote = f"{REMOTE_BASE}/{rel}"
    else:
        remote = f"{REMOTE_BASE}/{rel}"
    remote_dir = os.path.dirname(remote).replace("\\", "/")
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        parts = remote_dir.split("/")
        path = ""
        for p in parts:
            if not p:
                continue
            path += "/" + p
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)
    sftp.put(local, remote)
    print(f"Uploaded {rel}")

for local_fixture, remote_rel in FIXTURE_UPLOADS:
    if not os.path.isfile(local_fixture):
        continue
    remote = f"{REMOTE_BASE}/{remote_rel}"
    remote_dir = os.path.dirname(remote)
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)
    sftp.put(local_fixture, remote)
    print(f"Uploaded {remote_rel}")

sftp.close()

nginx_conf = os.path.join(LOCAL_BASE, "nginx", "toolbox.conf")
if os.path.isfile(nginx_conf):
    sftp = client.open_sftp()
    sftp.put(nginx_conf, "/etc/nginx/conf.d/toolbox.conf")
    sftp.close()
    print("Uploaded nginx/toolbox.conf")

commands = """
pip3.8 install opencv-python-headless pypdf PyMuPDF img2pdf python-docx pdf2docx pdfplumber==0.11.4 pdfminer.six==20231228 openpyxl volcengine -q
chmod +x /home/toolbox/monitor_check.py /home/toolbox/setup_monitor_cron.sh 2>/dev/null || true
test -f /home/toolbox/monitor.env || cp /home/toolbox/monitor.env.example /home/toolbox/monitor.env 2>/dev/null || true
bash /home/toolbox/setup_monitor_cron.sh 2>/dev/null || true
nginx -t && systemctl reload nginx
systemctl daemon-reload
systemctl enable toolbox
fuser -k 5000/tcp 2>/dev/null || true
sleep 1
systemctl restart toolbox
sleep 2
systemctl is-active toolbox
curl -s http://127.0.0.1:5000/api/health
echo
TOOLBOX_BASE=http://127.0.0.1:5000 python3.8 /home/toolbox/monitor_check.py || true
"""

stdin, stdout, stderr = client.exec_command(commands, timeout=300)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

client.close()
print("Deploy complete")