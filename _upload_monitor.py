#!/usr/bin/env python3
from ssh_helper import put, run

local = r"C:\Users\paz\toolbox-work\monitor_check.py"
remote = "/home/toolbox/monitor_check.py"
put(local, remote)
code, out, err = run(
    "chmod +x /home/toolbox/monitor_check.py && "
    "TOOLBOX_BASE=http://127.0.0.1:5000 /usr/bin/python3.8 /home/toolbox/monitor_check.py 2>&1 | tail -12",
    timeout=180,
)
print(out or err)