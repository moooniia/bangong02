import sys, re
sys.path.insert(0, r"C:\Users\paz\toolbox-work")
from ssh_helper import run

code, out, err = run(
    "journalctl -u toolbox --since '2026-06-11 00:00:00' --until '2026-06-12 00:00:00' --no-pager 2>/dev/null",
    timeout=60,
)
lines = out.splitlines()
starts = [l for l in lines if "走火山 OCR 智能文档解析" in l and "INFO in app" in l]
fails = [l for l in lines if "火山 OCR 失败" in l and "WARNING in app" in l]
scanned = [l for l in lines if "扫描件，OCR 识别可编辑文字" in l and "INFO in app" in l]

print("volc_ocr_starts", len(starts))
print("volc_ocr_fails", len(fails))
print("scanned_pdf_convert_requests", len(scanned))

# direct server scripts (not via app logger)
code2, out2, err2 = run(
    "grep -r 'pdf_to_markdown' /tmp/*.py /home/toolbox/*.py 2>/dev/null | head -5; "
    "ls -la /tmp/analyze_1212.py /tmp/diag_1212_remote.py 2>/dev/null",
    timeout=20,
)
print(out2 or err2)

# estimate pages: assume unknown mix; show if 12 vs 3 page
for n in (12, 3):
    print(f"if all {n}-page docs: {len(starts)*n} pages billed")

code3, out3, err3 = run(
    "journalctl -u toolbox --no-pager 2>/dev/null | grep '走火山 OCR 智能文档解析' | grep 'INFO in app' | wc -l",
    timeout=30,
)
print("all_time_starts", (out3 or err3).strip())