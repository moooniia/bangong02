#!/usr/bin/env python3
"""给所有前端 HTML 注入访问统计脚本（若尚未注入）。"""
import glob
import os

BASE = os.path.join(os.path.dirname(__file__), "server", "frontend")
TAG = '<script src="/assets/analytics.js" defer></script>'


def inject_file(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    if "analytics.js" in html:
        return False
    if "</head>" not in html:
        return False
    html = html.replace("</head>", f"  {TAG}\n</head>", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return True


def main():
    changed = 0
    for path in glob.glob(os.path.join(BASE, "*.html")):
        if inject_file(path):
            changed += 1
            print("injected", os.path.basename(path))
    print(f"done: {changed} files updated")


if __name__ == "__main__":
    main()