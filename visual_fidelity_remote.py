import json
import os
import subprocess
import sys
import tempfile

# runs on server
PDF = "/tmp/1212.pdf"
WPS = "/tmp/1212_wps.docx"
OURS = "/tmp/1212_full.docx"
OUT = "/tmp/visual_fidelity_report.json"
TXT = "/tmp/visual_fidelity_report.txt"

SCRIPT = r'''
import json, os, sys, tempfile
sys.path.insert(0, "/tmp")
os.chdir("/tmp")
from visual_fidelity_standard import run, format_report, PDF, WPS, OURS, OUT_JSON, OUT_MD
report = run(pdf="/tmp/1212.pdf", wps="/tmp/1212_wps.docx", ours="/tmp/1212_full.docx")
with open("/tmp/visual_fidelity_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
with open("/tmp/visual_fidelity_report.txt", "w", encoding="utf-8") as f:
    f.write(format_report(report))
print(format_report(report))
'''

if __name__ == "__main__":
    import ssh_helper
    ssh_helper.put(r"C:\Users\paz\toolbox-work\visual_fidelity_standard.py", "/tmp/visual_fidelity_standard.py")
    ssh_helper.put(r"C:\Users\paz\Desktop\1212.pdf", "/tmp/1212.pdf")
    ssh_helper.put(r"C:\Users\paz\Desktop\1212.docx", "/tmp/1212_wps.docx")
    ssh_helper.put(r"C:\Users\paz\Desktop\1212_full.docx", "/tmp/1212_full.docx")
    with open("/tmp/_vf_remote_runner.py", "w", encoding="utf-8") as f:
        f.write(SCRIPT.replace("OUT_JSON", '"/tmp/visual_fidelity_report.json"').replace("OUT_MD", '"/tmp/visual_fidelity_report.txt"'))
    ssh_helper.put("/tmp/_vf_remote_runner.py", "/tmp/_vf_remote_runner.py")
    code, out, err = ssh_helper.run("python3.8 /tmp/_vf_remote_runner.py", timeout=300)
    print(out or err)
    ssh_helper.fetch("/tmp/visual_fidelity_report.json", r"C:\Users\paz\toolbox-work\visual_fidelity_report.json")
    ssh_helper.fetch("/tmp/visual_fidelity_report.txt", r"C:\Users\paz\Desktop\1212验收标准报告.txt")