# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

- **VERSION** — 语义化版本（对外兼容级别）
- **BUILD** — 构建号 `年.月.日.序号`（每次部署递增）

## [Unreleased]

## [0.10.17] - 2026-06-13

构建号: `2026.06.13.2`

Fixed: v0.10.16b 在_add_html_table层应用行高（不依赖scoring_style检测）

### Fixed
- v0.10.16b 在_add_html_table层应用行高（不依赖scoring_style检测）

备份: `backups/v0.10.17/`


## [0.10.16] - 2026-06-13

构建号: `2026.06.13.1`

Fixed: v0.10.16 img2table行高检测+EMU→twips单位修复（解决2页bug）

### Fixed
- v0.10.16 img2table行高检测+EMU→twips单位修复（解决2页bug）

备份: `backups/v0.10.16/`


## [0.10.15] - 2026-06-12

构建号: `2026.06.12.24`

Fix OCR quality via fitz rotation matrix + proportional row heights from OpenCV line detection

### Changed
- Fix OCR quality via fitz rotation matrix + proportional row heights from OpenCV line detection

备份: `backups/v0.10.15/`


## [0.10.14] - 2026-06-12

构建号: `2026.06.12.23`

Fix: probe 90/270 even for sidebar pages, skip only 180 to prevent misflip

### Changed
- Fix: probe 90/270 even for sidebar pages, skip only 180 to prevent misflip

备份: `backups/v0.10.14/`


## [0.10.13] - 2026-06-12

构建号: `2026.06.12.22`

OSD rotation detection: Tesseract OSD as primary coarse rotation detector, visual heuristics as fallback

### Changed
- OSD rotation detection: Tesseract OSD as primary coarse rotation detector, visual heuristics as fallback

备份: `backups/v0.10.13/`


## [0.10.12] - 2026-06-12

构建号: `2026.06.12.21`

Fixed: page_4 考评打分表（左侧竖标题不翻180°、竖版A4表格样式）

### Fixed
- page_4 考评打分表（左侧竖标题不翻180°、竖版A4表格样式）

备份: `backups/v0.10.12/`


## [0.10.11] - 2026-06-12

构建号: `2026.06.12.20`

Added: 扫描校正支持90/180/270粗调+约12度歪斜细调（单页密集表）

### Added
- 扫描校正支持90/180/270粗调+约12度歪斜细调（单页密集表）

备份: `backups/v0.10.11/`


## [0.10.10] - 2026-06-12

构建号: `2026.06.12.19`

Fixed: 侧躺转正仅单页密集表触发，不误伤 B 任务清单

### Fixed
- 侧躺转正仅单页密集表触发，不误伤 B 任务清单

备份: `backups/v0.10.10/`


## [0.10.9] - 2026-06-12

构建号: `2026.06.12.18`

Added: 侧躺表格页分类与转正（与正坐表/真横版分开处理）

### Added
- 侧躺表格页分类与转正（与正坐表/真横版分开处理）

备份: `backups/v0.10.9/`


## [0.10.8] - 2026-06-12

构建号: `2026.06.12.17`

Fixed: 单页设备清单保持 PDF 竖版 A4 尺寸，不再擅自横版放大

### Fixed
- 单页设备清单保持 PDF 竖版 A4 尺寸，不再擅自横版放大

备份: `backups/v0.10.8/`


## [0.10.7] - 2026-06-12

构建号: `2026.06.12.16`

Fixed: 单页设备清单横版一页打完（去竖版标题节+压紧行高）

### Fixed
- 单页设备清单横版一页打完（去竖版标题节+压紧行高）

备份: `backups/v0.10.7/`


## [0.10.6] - 2026-06-12

构建号: `2026.06.12.15`

Fixed: 直传无有效内容时优先 PNG 重解析（page_6 设备清单表）

### Fixed
- 直传无有效内容时优先 PNG 重解析（page_6 设备清单表）

备份: `backups/v0.10.6/`


## [0.10.5] - 2026-06-12

构建号: `2026.06.12.14`

Fixed: 部署清单补上 seal_utils.py（签章抠图实际生效）

### Fixed
- 部署清单补上 seal_utils.py（签章抠图实际生效）

备份: `backups/v0.10.5/`


## [0.10.4] - 2026-06-12

构建号: `2026.06.12.13`

Fixed: 签章页红章圆环+星合成整框，剔除五角星碎片；签章页黑签名仅遮上半页 OCR 区

### Fixed
- 签章页红章圆环+星合成整框，剔除五角星碎片；签章页黑签名仅遮上半页 OCR 区

备份: `backups/v0.10.4/`


## [0.10.3] - 2026-06-12

构建号: `2026.06.12.12`

Fixed: 空textblocks不触发碎片PNG重解析

### Fixed
- 空textblocks不触发碎片PNG重解析

备份: `backups/v0.10.3/`


## [0.10.2] - 2026-06-12

构建号: `2026.06.12.11`

Fixed: 碎片检测签章碎片/空页分流

### Fixed
- 碎片检测签章碎片/空页分流

备份: `backups/v0.10.2/`


## [0.10.1] - 2026-06-12

构建号: `2026.06.12.10`

Fixed: 碎片检测不误伤C类+签章噪声过滤

### Fixed
- 碎片检测不误伤C类+签章噪声过滤

备份: `backups/v0.10.1/`


## [0.10.0] - 2026-06-12

构建号: `2026.06.12.9`

Added: P3签章页碎片检测PNG重解析+签章块清洗

### Added
- P3签章页碎片检测PNG重解析+签章块清洗

备份: `backups/v0.10.0/`


## [0.9.6] - 2026-06-12

构建号: `2026.06.12.8`

Fixed: 封面服务合同纵坐标按标题行数估算

### Fixed
- 封面服务合同纵坐标按标题行数估算

备份: `backups/v0.9.6/`


## [0.9.5] - 2026-06-12

构建号: `2026.06.12.7`

Fixed: 封面二维码PDF裁切、非蓝字黑色、标题字号位置

### Fixed
- 封面二维码PDF裁切、非蓝字黑色、标题字号位置

备份: `backups/v0.9.5/`


## [0.9.4] - 2026-06-12

构建号: `2026.06.12.6`

Fixed: 封面拆标题时去除水印碎片

### Fixed
- 封面拆标题时去除水印碎片

备份: `backups/v0.9.4/`


## [0.9.3] - 2026-06-12

构建号: `2026.06.12.5`

Fixed: 封面1页PDF不再撑出2页，绝对纵坐标定位

### Fixed
- 封面1页PDF不再撑出2页，绝对纵坐标定位

备份: `backups/v0.9.3/`


## [0.9.2] - 2026-06-12

构建号: `2026.06.12.4`

Fixed: 封面甲乙方拆行 y0 赋值错误

### Fixed
- 封面甲乙方拆行 y0 赋值错误

备份: `backups/v0.9.2/`


## [0.9.1] - 2026-06-12

构建号: `2026.06.12.3`

Added: P2封面第一页，去水印拆段+像素采样颜色字号

### Added
- P2封面第一页，去水印拆段+像素采样颜色字号

备份: `backups/v0.9.1/`


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