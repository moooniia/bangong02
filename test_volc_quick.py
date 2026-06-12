import sys
import urllib.request

sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import put, run

put(r"C:\Users\paz\Desktop\1212.pdf", "/tmp/1212.pdf")
put(r"C:\Users\paz\toolbox-work\server_convert_1212.py", "/tmp/server_convert_1212.py")
code, out, err = run("python3.8 /tmp/server_convert_1212.py", timeout=120)
print("volc_convert:", out or err, "exit", code)

try:
    with urllib.request.urlopen("http://139.196.28.78/api/health", timeout=10) as r:
        print("health:", r.read().decode())
except Exception as e:
    print("health_fail:", e)