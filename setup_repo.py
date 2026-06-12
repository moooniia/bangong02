#!/usr/bin/env python3
"""初始化 Git 仓库并创建基线 commit + v0.8.0 tag。"""
import subprocess
import sys

from versioning import ROOT, git_available, read_semver, release_tag

INITIAL_FILES = [
    ".gitignore",
    "VERSION",
    "BUILD",
    "CHANGELOG.md",
    "RELEASE.md",
    "versioning.py",
    "deploy_backend.py",
    "rollback.py",
    "smoke_test.py",
    "setup_repo.py",
    "server/backend",
]


def run(cmd, check=True):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True)


def main():
    if not git_available():
        print("未安装 Git，请先安装: https://git-scm.com/")
        sys.exit(1)

    if not run(["git", "init"], check=False).returncode == 0:
        print("git init 失败")
        sys.exit(1)

    run(["git", "config", "user.email", "toolbox@local"], check=False)
    run(["git", "config", "user.name", "Toolbox"], check=False)
    run(["git", "add", "-A"])
    r = run(["git", "commit", "-m", "chore: 初始化版本管理体系 v0.8.0"], check=False)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        print(r.stderr or r.stdout)
        sys.exit(1)

    tag = release_tag(read_semver())
    run(["git", "tag", "-a", tag, "-m", "baseline release 0.8.0"], check=False)
    print(f"完成。当前分支已就绪，基线 tag: {tag}")
    print("建议: 添加远程仓库后执行 git push && git push --tags")


if __name__ == "__main__":
    main()