#!/usr/bin/env python3
"""补拉服务器备份到指定 SemVer 备份目录。"""
import json
import os

import paramiko

from versioning import BACKUPS_DIR, DEPLOY_FILES, backup_dir_name, backup_server_files, read_semver

HOST = "139.196.28.78"
USER = "root"
PASS = "OpenClaw2026"


def main():
    release_dir = backup_dir_name(read_semver())
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    sftp = ssh.open_sftp()
    manifest = backup_server_files(
        sftp,
        release_dir,
        [remote for _, remote in DEPLOY_FILES],
    )
    sftp.close()
    ssh.close()

    manifest_path = os.path.join(BACKUPS_DIR, release_dir, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        data["server_before_deploy"] = manifest
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    ok = [m["name"] for m in manifest if not m.get("missing")]
    print(f"backups/{release_dir}/server/: {ok}")


if __name__ == "__main__":
    main()