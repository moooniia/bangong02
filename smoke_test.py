#!/usr/bin/env python3
"""部署前冒烟：语法检查 + 可选线上 A/B/C 样例验收。"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "server", "backend")

PY_FILES = [
    "volc_ocr.py",
    "app.py",
    "preprocessing.py",
    "seal_utils.py",
]


def compile_check() -> tuple[bool, str]:
    errors = []
    for name in PY_FILES:
        path = os.path.join(BACKEND, name)
        if not os.path.isfile(path):
            errors.append(f"缺少 {name}")
            continue
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", path],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            errors.append(f"{name}: {r.stderr.strip() or r.stdout.strip()}")
    if errors:
        return False, "编译检查失败:\n" + "\n".join(errors)
    return True, f"编译检查通过 ({len(PY_FILES)} 个核心文件)"


def online_abc_check() -> tuple[bool, str]:
    try:
        import requests
    except ImportError:
        return True, "跳过线上验收（未安装 requests）"

    cases = [
        (r"C:\Users\paz\Desktop\P T W 测试\B.pdf", "volc-image-table"),
        (r"C:\Users\paz\Desktop\P T W 测试\C.pdf", "volc-normal"),
    ]
    url = "http://139.196.28.78/api/convert"
    lines = []
    for path, expect in cases:
        if not os.path.isfile(path):
            lines.append(f"跳过 {os.path.basename(path)}（文件不存在）")
            continue
        with open(path, "rb") as f:
            r = requests.post(
                url,
                files={"file": (os.path.basename(path), f, "application/pdf")},
                data={"format": "docx"},
                timeout=300,
            )
        data = r.json()
        if not data.get("success"):
            return False, f"{os.path.basename(path)} 失败: {data}"
        route = data.get("route", "")
        if expect and route != expect:
            return False, f"{os.path.basename(path)} 路由异常: 期望 {expect} 实际 {route}"
        lines.append(f"OK {os.path.basename(path)} -> {route}")
    return True, "线上样例:\n" + "\n".join(lines)


def run_smoke(online: bool = False) -> tuple[bool, str]:
    ok, msg = compile_check()
    if not ok:
        return ok, msg
    parts = [msg]
    if online:
        ok2, msg2 = online_abc_check()
        parts.append(msg2)
        return ok2, "\n".join(parts)
    return True, "\n".join(parts)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--online", action="store_true", help="包含 B/C 线上 API 验收")
    args = p.parse_args()
    success, text = run_smoke(online=args.online)
    print(text)
    sys.exit(0 if success else 1)