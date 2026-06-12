
import json, sys
sys.path.insert(0, '/tmp')
from visual_fidelity_standard import run, format_report
r = run('/tmp/1212.pdf', '/tmp/1212_wps.docx', '/tmp/1212_full.docx')
open('/tmp/visual_fidelity_report.json','w',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2))
open('/tmp/visual_fidelity_report.txt','w',encoding='utf-8').write(format_report(r))
print(format_report(r))
