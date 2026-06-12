#!/usr/bin/env python3
"""发布部署：冒烟测试 → 备份 → SemVer → 上传 → Git tag。"""
import argparse
import os
import sys

import paramiko

from smoke_test import run_smoke
from versioning import (
    BACKEND_DIR,
    DEPLOY_FILES,
    append_release_changelog,
    backup_dir_name,
    backup_local_sources,
    backup_server_files,
    bump_semver,
    git_available,
    git_is_repo,
    git_tag_release,
    next_build,
    read_build,
    read_semver,
    release_tag,
    write_build,
    write_manifest,
    write_semver,
)

HOST = "139.196.28.78"
USER = "root"
PASS = "OpenClaw2026"


def deploy_files(sftp):
    for name, remote in DEPLOY_FILES:
        local = os.path.join(BACKEND_DIR, name)
        sftp.put(local, remote)
        print(f"Uploaded: {name}")


def restart_service(ssh):
    _, out, _ = ssh.exec_command(
        "systemctl restart toolbox && sleep 2 && systemctl is-active toolbox"
    )
    return out.read().decode().strip()


def main():
    parser = argparse.ArgumentParser(description="部署办公工具箱后端")
    parser.add_argument("note", help="本次发布说明（支持 Added:/Fixed:/Changed: 分段）")
    parser.add_argument(
        "--bump",
        choices=("patch", "minor", "major"),
        default="patch",
        help="SemVer 递增级别（默认 patch）",
    )
    parser.add_argument("--skip-smoke", action="store_true", help="跳过部署前冒烟测试")
    parser.add_argument("--no-tag", action="store_true", help="不创建 Git tag")
    args = parser.parse_args()

    note = args.note.strip()
    if not note:
        print("错误: 必须提供发布说明")
        sys.exit(1)

    if not args.skip_smoke:
        print("=== 冒烟测试 ===")
        ok, msg = run_smoke(online=False)
        print(msg)
        if not ok:
            print("冒烟未通过，已中止部署。可用 --skip-smoke 强制（不推荐）")
            sys.exit(1)

    old_semver = read_semver()
    new_semver = bump_semver(old_semver, args.bump)
    new_build = next_build(read_build())
    release_dir = backup_dir_name(new_semver)
    tag = release_tag(new_semver)

    print(f"SemVer: {old_semver} -> {new_semver}  ({tag})")
    print(f"BUILD:  {read_build() or '(无)'} -> {new_build}")
    print(f"说明:   {note}")

    local_manifest = backup_local_sources(release_dir)
    print(f"已备份本地 {len(local_manifest)} 个文件 -> backups/{release_dir}/local/")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)

    sftp = ssh.open_sftp()
    server_manifest = backup_server_files(
        sftp,
        release_dir,
        [remote for _, remote in DEPLOY_FILES],
    )
    saved = sum(1 for m in server_manifest if not m.get("missing"))
    print(f"已备份服务器 {saved} 个文件 -> backups/{release_dir}/server/")

    deploy_files(sftp)
    sftp.close()

    manifest_path = write_manifest(
        release_dir,
        new_semver,
        new_build,
        local_manifest,
        server_manifest,
        note,
    )
    write_semver(new_semver)
    write_build(new_build)
    append_release_changelog(new_semver, new_build, note)
    print(f"已更新 VERSION={new_semver} BUILD={new_build}")
    print(f"已写入 CHANGELOG、{manifest_path}")

    service = restart_service(ssh)
    print("Service:", service)
    ssh.close()

    if not args.no_tag and git_is_repo():
        if git_tag_release(new_semver, note):
            print(f"Git tag: {tag}")
        else:
            print("Git tag 创建失败（可能无新 commit 或 tag 已存在）")
    elif not git_is_repo():
        print("提示: 尚未初始化 Git，运行 python setup_repo.py")

    print(f"Done. 已发布 {tag} (build {new_build})")


if __name__ == "__main__":
    main()