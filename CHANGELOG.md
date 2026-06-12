# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

- **VERSION** — 语义化版本（对外兼容级别）
- **BUILD** — 构建号 `年.月.日.序号`（每次部署递增）

## [Unreleased]

## [0.9.0] - 2026-06-12

构建号: `2026.06.12.2`

Added: A合同P1同页双通道，正文detail坐标+markdown表格择优
Changed: 密集表页有正文时保留版式抠章

### Added
- A合同P1同页双通道，正文detail坐标+markdown表格择优

### Changed
- 密集表页有正文时保留版式抠章

备份: `backups/v0.9.0/`


## [0.8.0] - 2026-06-12

构建号: `2026.06.12.1`

基线生产版本（版本管理体系启用前已上线能力）。

### Added
- PDF→Word 智能路由：电子版本地 / 扫描件火山 API
- A 合同：`volc-hybrid`（抠章、版式、逐页 PNG detail）
- B 任务清单：`volc-image-table`（蓝表头/红章节配色）
- C 作文：`volc-normal`（颜色字号）
- P0：空白页截图兜底、密集表页独立策略、warning 回传
- 部署前自动备份到 `backups/v{semver}/`

### Changed
- 扫描件统一走 tier-2 火山 OCR
- `deploy_backend.py` 强制填写部署说明

备份: `backups/2026.06.12.1/`（旧格式目录，内容等同 v0.8.0 基线）