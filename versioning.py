"""版本与发布管理：SemVer + BUILD、备份、CHANGELOG（Keep a Changelog）。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import date, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(ROOT, "VERSION")
BUILD_FILE = os.path.join(ROOT, "BUILD")
CHANGELOG_FILE = os.path.join(ROOT, "CHANGELOG.md")
BACKUPS_DIR = os.path.join(ROOT, "backups")
BACKEND_DIR = os.path.join(ROOT, "server", "backend")

BACKEND_SOURCES = [
    "volc_ocr.py",
    "app.py",
    "preprocessing.py",
    "seal_utils.py",
    "pdf_utils.py",
    "ocr_utils.py",
    "image_utils.py",
    "file_utils.py",
    "usage_stats.py",
]

# 直接从 BACKEND_SOURCES 派生，避免两份清单手动维护、漏改其中一份导致改了文件却没真正部署
DEPLOY_FILES = [(name, f"/home/toolbox/backend/{name}") for name in BACKEND_SOURCES]

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
BUILD_RE = re.compile(r"^(\d{4}\.\d{2}\.\d{2})\.(\d+)$")


def read_semver() -> str:
    if not os.path.isfile(VERSION_FILE):
        return "0.0.0"
    line = open(VERSION_FILE, encoding="utf-8").read().strip().splitlines()[0].strip()
    if SEMVER_RE.fullmatch(line):
        return line
    return "0.0.0"


def read_build() -> str:
    if not os.path.isfile(BUILD_FILE):
        return ""
    return open(BUILD_FILE, encoding="utf-8").read().strip()


def write_semver(version: str) -> None:
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version.strip() + "\n")


def write_build(build_id: str) -> None:
    with open(BUILD_FILE, "w", encoding="utf-8") as f:
        f.write(build_id.strip() + "\n")


def bump_semver(current: str, level: str = "patch") -> str:
    m = SEMVER_RE.fullmatch((current or "0.0.0").strip())
    if not m:
        return "0.0.1"
    major, minor, patch = (int(m.group(i)) for i in range(1, 4))
    level = (level or "patch").lower()
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def next_build(current: str = "") -> str:
    today = date.today().strftime("%Y.%m.%d")
    current = (current or read_build()).strip()
    m = BUILD_RE.fullmatch(current)
    if m and m.group(1) == today:
        return f"{today}.{int(m.group(2)) + 1}"
    return f"{today}.1"


def release_tag(semver: str) -> str:
    return f"v{semver}"


def backup_dir_name(semver: str) -> str:
    return release_tag(semver)


def list_backup_releases() -> list[dict]:
    if not os.path.isdir(BACKUPS_DIR):
        return []
    rows = []
    for name in sorted(os.listdir(BACKUPS_DIR), reverse=True):
        path = os.path.join(BACKUPS_DIR, name)
        if not os.path.isdir(path):
            continue
        manifest_path = os.path.join(path, "manifest.json")
        meta = {"dir": name, "path": path, "semver": "", "build": "", "created_at": ""}
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    data = json.load(f)
                meta.update({
                    "semver": data.get("semver") or data.get("version") or "",
                    "build": data.get("build") or "",
                    "created_at": data.get("created_at") or "",
                    "note": (data.get("note") or "")[:120],
                })
            except (json.JSONDecodeError, OSError):
                pass
        rows.append(meta)
    return rows


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_file(src: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)


def backup_local_sources(release_dir: str) -> list[dict]:
    dest_root = os.path.join(BACKUPS_DIR, release_dir, "local")
    manifest = []
    for name in BACKEND_SOURCES:
        src = os.path.join(BACKEND_DIR, name)
        if not os.path.isfile(src):
            continue
        dest = os.path.join(dest_root, name)
        _copy_file(src, dest)
        manifest.append({
            "name": name,
            "path": dest,
            "sha256": _sha256(src),
            "size": os.path.getsize(src),
        })
    return manifest


def backup_server_files(sftp, release_dir: str, remotes: list[str]) -> list[dict]:
    dest_root = os.path.join(BACKUPS_DIR, release_dir, "server")
    os.makedirs(dest_root, exist_ok=True)
    manifest = []
    for remote in remotes:
        name = os.path.basename(remote)
        dest = os.path.join(dest_root, name)
        try:
            sftp.get(remote, dest)
            manifest.append({
                "name": name,
                "remote": remote,
                "path": dest,
                "sha256": _sha256(dest),
                "size": os.path.getsize(dest),
            })
        except Exception as exc:
            manifest.append({
                "name": name,
                "remote": remote,
                "missing": True,
                "error": str(exc),
            })
    return manifest


def write_manifest(
    release_dir: str,
    semver: str,
    build_id: str,
    local_manifest: list,
    server_manifest: list,
    note: str,
    change_types: dict | None = None,
) -> str:
    payload = {
        "semver": semver,
        "build": build_id,
        "tag": release_tag(semver),
        "version": semver,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "note": note,
        "change_types": change_types or {},
        "local": local_manifest,
        "server_before_deploy": server_manifest,
    }
    path = os.path.join(BACKUPS_DIR, release_dir, "manifest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def _ensure_changelog_header() -> None:
    if os.path.isfile(CHANGELOG_FILE):
        return
    header = (
        "# Changelog\n\n"
        "本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，"
        "版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。\n\n"
        "构建号见 `BUILD`（`年.月.日.序号`）。\n\n"
        "## [Unreleased]\n\n"
    )
    with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
        f.write(header)


def append_release_changelog(
    semver: str,
    build_id: str,
    note: str,
    change_types: dict | None = None,
) -> None:
    """在 [Unreleased] 之后插入新版本条目。"""
    _ensure_changelog_header()
    today = date.today().isoformat()
    sections = change_types or _parse_change_types(note)

    body_lines = [f"## [{semver}] - {today}\n", f"\n构建号: `{build_id}`\n"]
    if note.strip():
        body_lines.append("\n" + note.strip() + "\n")
    typed = False
    for key, title in (
        ("added", "### Added"),
        ("changed", "### Changed"),
        ("fixed", "### Fixed"),
        ("removed", "### Removed"),
        ("security", "### Security"),
    ):
        items = sections.get(key) or []
        if items:
            typed = True
            body_lines.append("\n" + title + "\n")
            for item in items:
                body_lines.append(f"- {item}\n")
    if not typed and not note.strip():
        body_lines.append("\n### Changed\n- 例行发布\n")
    body_lines.append(f"\n备份: `backups/v{semver}/`\n\n")
    new_entry = "".join(body_lines)

    with open(CHANGELOG_FILE, encoding="utf-8") as f:
        content = f.read()

    marker = "## [Unreleased]"
    if marker in content:
        idx = content.index(marker)
        tail = content[idx + len(marker) :]
        next_hdr = re.search(r"\n## \[", tail)
        insert_pos = idx + len(marker) + (next_hdr.start() if next_hdr else len(tail))
        content = content[:insert_pos] + "\n" + new_entry + content[insert_pos:]
    else:
        content = content.rstrip() + "\n\n" + new_entry

    with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def _parse_change_types(note: str) -> dict:
    """从部署说明中提取 Added/Changed/Fixed 条目（行首 - 或 *）。"""
    sections = {"added": [], "changed": [], "fixed": [], "removed": [], "security": []}
    current = "changed"
    for line in (note or "").splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith("added:") or low.startswith("新增:"):
            current = "added"
            s = s.split(":", 1)[-1].strip()
            if s:
                sections[current].append(s)
            continue
        if low.startswith("changed:") or low.startswith("变更:"):
            current = "changed"
            s = s.split(":", 1)[-1].strip()
            if s:
                sections[current].append(s)
            continue
        if low.startswith("fixed:") or low.startswith("修复:"):
            current = "fixed"
            s = s.split(":", 1)[-1].strip()
            if s:
                sections[current].append(s)
            continue
        if s.startswith("-") or s.startswith("*"):
            sections[current].append(s.lstrip("-* ").strip())
        elif not sections[current]:
            sections[current].append(s)
    return sections


def restore_local_from_backup(release_dir: str, source: str = "local") -> list[str]:
    """从 backups 恢复文件到 server/backend。source: local | server"""
    src_root = os.path.join(BACKUPS_DIR, release_dir, source)
    if not os.path.isdir(src_root):
        raise FileNotFoundError(f"备份不存在: {src_root}")
    restored = []
    for name in BACKEND_SOURCES:
        src = os.path.join(src_root, name)
        if not os.path.isfile(src):
            continue
        dest = os.path.join(BACKEND_DIR, name)
        _copy_file(src, dest)
        restored.append(name)
    return restored


def git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            cwd=ROOT,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def git_is_repo() -> bool:
    return os.path.isdir(os.path.join(ROOT, ".git"))


def git_tag_release(semver: str, message: str) -> bool:
    if not git_is_repo():
        return False
    tag = release_tag(semver)
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=False)
    subprocess.run(
        ["git", "commit", "-m", f"release: {tag} {message[:80]}"],
        cwd=ROOT,
        check=False,
    )
    r = subprocess.run(
        ["git", "tag", "-a", tag, "-m", message],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0