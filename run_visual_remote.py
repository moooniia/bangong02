import sys
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import put, run, fetch

put(r"C:\Users\paz\toolbox-work\visual_fidelity_standard.py", "/tmp/visual_fidelity_standard.py")
put(r"C:\Users\paz\Desktop\1212.pdf", "/tmp/1212.pdf")
put(r"C:\Users\paz\Desktop\1212.docx", "/tmp/1212_wps.docx")
put(r"C:\Users\paz\Desktop\1212_full.docx", "/tmp/1212_full.docx")

runner = """
import json, sys
sys.path.insert(0, '/tmp')
from visual_fidelity_standard import run, format_report
r = run('/tmp/1212.pdf', '/tmp/1212_wps.docx', '/tmp/1212_full.docx')
open('/tmp/visual_fidelity_report.json','w',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2))
open('/tmp/visual_fidelity_report.txt','w',encoding='utf-8').write(format_report(r))
print(format_report(r))
"""
with open(r"C:\Users\paz\toolbox-work\_vf_run.py", "w", encoding="utf-8") as f:
    f.write(runner)
put(r"C:\Users\paz\toolbox-work\_vf_run.py", "/tmp/_vf_run.py")
code, out, err = run("python3.8 /tmp/_vf_run.py", timeout=300)
print(out or err)
fetch("/tmp/visual_fidelity_report.json", r"C:\Users\paz\toolbox-work\visual_fidelity_report.json")
fetch("/tmp/visual_fidelity_report.txt", r"C:\Users\paz\Desktop\1212验收标准报告.txt")