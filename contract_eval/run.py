#!/usr/bin/env python3
"""一键：建 GT → 导出预测 → 评测。"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)


def _run(cmd):
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="1212")
    ap.add_argument("--pdf", default=r"C:\Users\paz\Desktop\1212.pdf")
    ap.add_argument("--ref-docx", default=r"C:\Users\paz\Desktop\1212.docx")
    ap.add_argument("--pred-docx", default="")
    ap.add_argument("--skip-build-gt", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    ce = os.path.join(HERE)

    if not args.skip_build_gt:
        _run([py, os.path.join(ce, "build_gt.py"), "--id", args.id, "--pdf", args.pdf, "--ref-docx", args.ref_docx])

    pred_docx = args.pred_docx or os.path.join(ROOT, "1212_full.docx")
    if not os.path.isfile(pred_docx):
        pred_docx = r"C:\Users\paz\Desktop\1212_full.docx"

    _run([py, os.path.join(ce, "export_preds.py"), "--id", args.id, "--docx", pred_docx])
    _run([py, os.path.join(ce, "eval.py"), "--id", args.id])


if __name__ == "__main__":
    main()