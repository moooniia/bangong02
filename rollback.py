#!/usr/bin/env python3
"""回滚到指定 SemVer 备份并可选重新部署。"""
import argparse
import os
import sys

import paramiko

from versioning import (
    BACKEND_DIR,
    DEPLOY_FILES,
    backup_dir_name,
    list_backup_releases,
    read_semver,
    release_tag,
    restore_local_from_backup,
)

HOST = "139.196.28.78"
USER = "root"
PASS = "OpenClaw2026"


def list_releases():
    rows = list_backup_releases()
    print("可用备份:")
    if not rows:
        print("  (无)")
        return
    for r in rows:
        semver = r.get("semver") or r.get("dir", "")
        build = r.get("build") or "-"
        created = (r.get("created_at") or "")[:19]
        note = r.get("note") or ""
        print(f"  {r['dir']:20}  semver={semver}  build={build}  {created}  {note}")


def resolve_release_dir(target: str) -> str:
    target = target.strip().lstrip("v")
    if os.path.isdir(os.path.join(os.path.dirname(__file__), "backups", f"v{target}")):
        return f"v{target}"
    if os.path.isdir(os.path.join(os.path.dirname(__file__), "backups", target)):
        return target
    for r in list_backup_releases():
        if r.get("semver") == target or r.get("dir") in (target, f"v{target}"):
            return r["dir"]
    raise FileNotFoundError(f"找不到备份: {target}")


def deploy_restored():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    sftp = ssh.open_sftp()
    for name, remote in DEPLOY_FILES:
        local = os.path.join(BACKEND_DIR, name)
        if os.path.isfile(local):
            sftp.put(local, remote)
            print(f"Uploaded: {name}")
    sftp.close()
    _, out, _ = ssh.exec_command(
        "systemctl restart toolbox && sleep 2 && systemctl is-active toolbox"
    )
    print("Service:", out.read().decode().strip())
    ssh.close()


def main():
    parser = argparse.ArgumentParser(description="回滚到历史备份版本")
    parser.add_argument("target", nargs="?", help="SemVer 如 0.8.0 或备份目录名")
    parser.add_argument("--list", action="store_true", help="列出可用备份")
    parser.add_argument("--no-deploy", action="store_true", help="只恢复本地，不上传服务器")
    parser.add_argument(
        "--source",
        choices=("local", "server"),
        default="local",
        help="从备份的 local 还是 server 子目录恢复（默认 local）",
    )
    args = parser.parse_args()

    if args.list or not args.target:
        list_releases()
        if not args.target:
            print(f"\n当前 VERSION: {read_semver()}")
        return

    release_dir = resolve_release_dir(args.target)
    print(f"回滚目标: backups/{release_dir}/ ({args.source})")

    restored = restore_local_from_backup(release_dir, source=args.source)
    print(f"已恢复本地: {', '.join(restored)}")

    if not args.no_deploy:
        deploy_restored()
        print("已部署到服务器。")
    else:
        print("仅本地恢复。部署请运行: python deploy_backend.py \"回滚后确认部署\"")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)