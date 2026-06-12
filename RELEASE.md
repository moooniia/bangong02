# 发布与版本管理

本工程采用业界通用的 **Git + SemVer + Keep a Changelog + 部署备份** 体系。

## 文件说明

| 文件 | 含义 |
|------|------|
| `VERSION` | 语义化版本 `主.次.修订`（如 `0.8.1`） |
| `BUILD` | 构建号 `年.月.日.序号`（如 `2026.06.12.2`） |
| `CHANGELOG.md` | 面向人的变更记录（Keep a Changelog 格式） |
| `backups/vX.Y.Z/` | 每次发布的不可变代码快照 |

## 日常开发

1. 在 `CHANGELOG.md` 的 **`[Unreleased]`** 下记录改动
2. 改 `server/backend/` 代码
3. 本地验证（A/B/C 样例）

## 发布（部署到服务器）

```powershell
cd C:\Users\paz\toolbox-work

# 标准发布（patch + 编译冒烟 + 备份 + 部署 + Git tag）
python deploy_backend.py "Fixed: 修复第4页空白"

# 带分类的说明（自动写入 CHANGELOG 对应小节）
python deploy_backend.py "Added: 双通道表格`nFixed: 签章页兜底" --bump minor

# 跳过冒烟（仅紧急时）
python deploy_backend.py "Hotfix: ..." --skip-smoke
```

**SemVer 递增规则**（[semver.org](https://semver.org/lang/zh-CN/)）：

- `--bump patch`（默认）：修 bug、小优化
- `--bump minor`：新功能、向下兼容
- `--bump major`：破坏性变更

## 回滚

```powershell
# 列出备份
python rollback.py --list

# 恢复到 v0.8.0 并重新部署
python rollback.py 0.8.0

# 只恢复本地不上传
python rollback.py 0.8.0 --no-deploy
```

## 冒烟测试

```powershell
# 仅编译检查（deploy 默认执行）
python smoke_test.py

# 含 B/C 线上 API 验收（较慢）
python smoke_test.py --online
```

## Git 初始化（首次）

```powershell
python setup_repo.py
```

之后每次 `deploy_backend.py` 会自动 `git tag vX.Y.Z`。

## 3-2-1 备份建议

1. **Git** — 完整修改历史（本地 + 建议推送到私有远程仓库）
2. **backups/** — 每次部署瞬间快照（本地磁盘）
3. **异地** — 定期将 Git 远程或 `backups/` 同步到网盘/第二台机器