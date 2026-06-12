#!/usr/bin/env python3
"""将当前代码建档为 SemVer 备份目录 v0.8.0（不部署）。"""
import paramiko

from versioning import (
    DEPLOY_FILES,
    append_release_changelog,
    backup_dir_name,
    backup_local_sources,
    backup_server_files,
    read_build,
    read_semver,
    write_manifest,
)

HOST = "139.196.28.78"
USER = "root"
PASS = "OpenClaw2026"
NOTE = "基线快照（migrate to SemVer backup layout）"


def main():
    semver = read_semver()
    build_id = read_build()
    release_dir = backup_dir_name(semver)
    local_manifest = backup_local_sources(release_dir)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    sftp = ssh.open_sftp()
    server_manifest = backup_server_files(
        sftp,
        release_dir,
        [remote for _, remote in DEPLOY_FILES],
    )
    sftp.close()
    ssh.close()

    write_manifest(release_dir, semver, build_id, local_manifest, server_manifest, NOTE)
    print(f"已建档 backups/{release_dir}/")


if __name__ == "__main__":
    main()