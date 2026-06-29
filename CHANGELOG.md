# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

- **VERSION** — 语义化版本（对外兼容级别）
- **BUILD** — 构建号 `年.月.日.序号`（每次部署递增）

## [Unreleased]

## [0.12.26] - 2026-06-29

构建号: `2026.06.29.1`

feat: PDF编辑器压缩支持目标体积(5MB/2MB以下)，用Ghostscript逐档压缩

### Changed
- feat: PDF编辑器压缩支持目标体积(5MB/2MB以下)，用Ghostscript逐档压缩

备份: `backups/v0.12.26/`


## [0.12.25] - 2026-06-28

构建号: `2026.06.28.1`

feat: PDF转图片只有1页时直接给图片，多页才打包压缩包

### Changed
- feat: PDF转图片只有1页时直接给图片，多页才打包压缩包

备份: `backups/v0.12.25/`


## [0.12.24] - 2026-06-25

构建号: `2026.06.25.3`

fix: 图片转PDF统一A4/A3页面大小时，旋转90/270度的图片没跟着把页面换成横向，导致上下留白

### Changed
- fix: 图片转PDF统一A4/A3页面大小时，旋转90/270度的图片没跟着把页面换成横向，导致上下留白

备份: `backups/v0.12.24/`


## [0.12.23] - 2026-06-25

构建号: `2026.06.25.2`

feat: 图片转PDF升级成编辑器UX，支持单张旋转/拖拽排序/统一A3A4页面大小

### Changed
- feat: 图片转PDF升级成编辑器UX，支持单张旋转/拖拽排序/统一A3A4页面大小

备份: `backups/v0.12.23/`


## [0.12.22] - 2026-06-25

构建号: `2026.06.25.1`

fix: PDF编辑器导出旋转方向跟预览不一致——show_pdf_page的rotate参数没叠加源页面自带的/Rotate角度

### Changed
- fix: PDF编辑器导出旋转方向跟预览不一致——show_pdf_page的rotate参数没叠加源页面自带的/Rotate角度

备份: `backups/v0.12.22/`


## [0.12.21] - 2026-06-23

构建号: `2026.06.23.2`

fix: 意见反馈飞书推送结果加print日志，确认是否真的送达

### Changed
- fix: 意见反馈飞书推送结果加print日志，确认是否真的送达

备份: `backups/v0.12.21/`


## [0.12.20] - 2026-06-23

构建号: `2026.06.23.1`

feat: 新增意见反馈功能，提交后推送到飞书

### Changed
- feat: 新增意见反馈功能，提交后推送到飞书

备份: `backups/v0.12.20/`


## [0.12.19] - 2026-06-22

构建号: `2026.06.22.1`

feat: 新增付费API调用次数统计(usage_stats.py)，覆盖火山OCR(Word/Excel/文字识别)和翻译

### Changed
- feat: 新增付费API调用次数统计(usage_stats.py)，覆盖火山OCR(Word/Excel/文字识别)和翻译

备份: `backups/v0.12.19/`


## [0.12.18] - 2026-06-21

构建号: `2026.06.21.1`

feat: 新增图片旋转工具，去掉Office文档互转(与PDF板块重复)，首页排版优化

### Changed
- feat: 新增图片旋转工具，去掉Office文档互转(与PDF板块重复)，首页排版优化

备份: `backups/v0.12.18/`


## [0.12.17] - 2026-06-19

构建号: `2026.06.19.9`

fix: OCR调试日志改用print，因为app.logger.info在这个项目里不会输出到journalctl

### Changed
- fix: OCR调试日志改用print，因为app.logger.info在这个项目里不会输出到journalctl

备份: `backups/v0.12.17/`


## [0.12.16] - 2026-06-19

构建号: `2026.06.19.8`

feat: OCR路由加日志，记录每次请求是否触发火山OCR兜底

### Changed
- feat: OCR路由加日志，记录每次请求是否触发火山OCR兜底

备份: `backups/v0.12.16/`


## [0.12.15] - 2026-06-19

构建号: `2026.06.19.7`

fix: 用低置信度词占比代替平均置信度触发火山OCR兜底，更准确抓出夹在好文字里的零星错字

### Changed
- fix: 用低置信度词占比代替平均置信度触发火山OCR兜底，更准确抓出夹在好文字里的零星错字

备份: `backups/v0.12.15/`


## [0.12.14] - 2026-06-19

构建号: `2026.06.19.6`

feat: OCR置信度低时自动回退火山OCR兜底

### Changed
- feat: OCR置信度低时自动回退火山OCR兜底

备份: `backups/v0.12.14/`


## [0.12.13] - 2026-06-19

构建号: `2026.06.19.5`

perf: 大图跳过去噪+降低OCR多轮重试提前退出阈值，缩短识别耗时

### Changed
- perf: 大图跳过去噪+降低OCR多轮重试提前退出阈值，缩短识别耗时

备份: `backups/v0.12.13/`


## [0.12.12] - 2026-06-19

构建号: `2026.06.19.4`

fix: 切块OCR去重叠重复行

### Changed
- fix: 切块OCR去重叠重复行

备份: `backups/v0.12.12/`


## [0.12.11] - 2026-06-19

构建号: `2026.06.19.3`

fix: OCR过滤高饱和度表情符号/彩色图标，避免污染相邻文字识别

### Changed
- fix: OCR过滤高饱和度表情符号/彩色图标，避免污染相邻文字识别

备份: `backups/v0.12.11/`


## [0.12.10] - 2026-06-19

构建号: `2026.06.19.2`

fix: OCR深色背景截图反色识别+图片转文字/扫描件转文字上传与复制反馈优化

### Changed
- fix: OCR深色背景截图反色识别+图片转文字/扫描件转文字上传与复制反馈优化

备份: `backups/v0.12.10/`


## [0.12.9] - 2026-06-19

构建号: `2026.06.19.1`

feat: PDF编辑器新增大图预览接口/api/pdf/editor/preview

### Changed
- feat: PDF编辑器新增大图预览接口/api/pdf/editor/preview

备份: `backups/v0.12.9/`


## [0.12.8] - 2026-06-15

构建号: `2026.06.15.6`

remove snapshot warning and Strategy B watermark false positive

### Changed
- remove snapshot warning and Strategy B watermark false positive

备份: `backups/v0.12.8/`


## [0.12.7] - 2026-06-15

构建号: `2026.06.15.5`

fix: watermark docs skip direct mode, use image-mode OCR directly

### Changed
- fix: watermark docs skip direct mode, use image-mode OCR directly

备份: `backups/v0.12.7/`


## [0.12.6] - 2026-06-15

构建号: `2026.06.15.4`

fix: watermark scanned docs skip OCR use image-embed directly

### Changed
- fix: watermark scanned docs skip OCR use image-embed directly

备份: `backups/v0.12.6/`


## [0.12.5] - 2026-06-15

构建号: `2026.06.15.3`

fix: per-page DPI fallback when Volcano API rejects large image

### Changed
- fix: per-page DPI fallback when Volcano API rejects large image

备份: `backups/v0.12.5/`


## [0.12.4] - 2026-06-15

构建号: `2026.06.15.2`

红章G阈值放宽+print日志

### Changed
- 红章G阈值放宽+print日志

备份: `backups/v0.12.4/`


## [0.12.3] - 2026-06-15

构建号: `2026.06.15.1`

文字层含红章时走火山OCR

### Changed
- 文字层含红章时走火山OCR

备份: `backups/v0.12.3/`


## [0.12.2] - 2026-06-13

构建号: `2026.06.13.42`

per-page rotation, pdf-grid layout

### Changed
- per-page rotation, pdf-grid layout

备份: `backups/v0.12.2/`


## [0.12.1] - 2026-06-13

构建号: `2026.06.13.41`

Added: rotate/compress in pdf_editor_export; decrypt encrypted PDF on thumbnail upload

### Added
- rotate/compress in pdf_editor_export; decrypt encrypted PDF on thumbnail upload

备份: `backups/v0.12.1/`


## [0.12.0] - 2026-06-13

构建号: `2026.06.13.40`

Added: PDF Editor - thumbnail endpoint, export endpoint, pdf_utils pdf_thumbnails+pdf_editor_export, index.html consolidation

### Added
- PDF Editor - thumbnail endpoint, export endpoint, pdf_utils pdf_thumbnails+pdf_editor_export, index.html consolidation

备份: `backups/v0.12.0/`


## [0.10.36] - 2026-06-13

构建号: `2026.06.13.21`

v0.10.36: compact单页dense表用WPS列宽比例兜底，移除debug日志

### Changed
- v0.10.36: compact单页dense表用WPS列宽比例兜底，移除debug日志

备份: `backups/v0.10.36/`


## [0.10.35] - 2026-06-13

构建号: `2026.06.13.20`

debug2: 查parsed前3行

### Changed
- debug2: 查parsed前3行

备份: `backups/v0.10.35/`


## [0.10.34] - 2026-06-13

构建号: `2026.06.13.19`

debug: 临时日志查page_4-1的scoring检测路径

### Changed
- debug: 临时日志查page_4-1的scoring检测路径

备份: `backups/v0.10.34/`


## [0.10.33] - 2026-06-13

构建号: `2026.06.13.18`

v0.10.33: 单页scoring/dense表后处理，限制段落space_before≤20pt防止Y坐标推到第二页

### Changed
- v0.10.33: 单页scoring/dense表后处理，限制段落space_before≤20pt防止Y坐标推到第二页

备份: `backups/v0.10.33/`


## [0.10.32] - 2026-06-13

构建号: `2026.06.13.17`

v0.10.32: scoring表去除行颜色，行高改exact防止撑出第二页

### Changed
- v0.10.32: scoring表去除行颜色，行高改exact防止撑出第二页

备份: `backups/v0.10.32/`


## [0.10.31] - 2026-06-13

构建号: `2026.06.13.16`

v0.10.31: 修复scoring表识别——检查前3行而非只检查第0行，扩充header关键词集

### Changed
- v0.10.31: 修复scoring表识别——检查前3行而非只检查第0行，扩充header关键词集

备份: `backups/v0.10.31/`


## [0.10.30] - 2026-06-13

构建号: `2026.06.13.15`

v0.10.30: 6列考评表加WPS列宽比例，scoring_style无比例时用内容估算兜底

### Changed
- v0.10.30: 6列考评表加WPS列宽比例，scoring_style无比例时用内容估算兜底

备份: `backups/v0.10.30/`


## [0.10.29] - 2026-06-13

构建号: `2026.06.13.14`

v0.10.29: 列宽改用内容文字长度估算(sqrt权重)，img2table检测不到6列时回退

### Changed
- v0.10.29: 列宽改用内容文字长度估算(sqrt权重)，img2table检测不到6列时回退

备份: `backups/v0.10.29/`


## [0.10.28] - 2026-06-13

构建号: `2026.06.13.13`

debug: 临时日志查col_widths检测结果

### Changed
- debug: 临时日志查col_widths检测结果

备份: `backups/v0.10.28/`


## [0.10.27] - 2026-06-13

构建号: `2026.06.13.12`

v0.10.27: img2table检测列宽比例，单页密集表按内容分配列宽而非六等分

### Changed
- v0.10.27: img2table检测列宽比例，单页密集表按内容分配列宽而非六等分

备份: `backups/v0.10.27/`


## [0.10.26] - 2026-06-13

构建号: `2026.06.13.11`

v0.10.26: 单页密集表行高exact防膨胀，10行以下字号8pt，compact不限制小表字号

### Changed
- v0.10.26: 单页密集表行高exact防膨胀，10行以下字号8pt，compact不限制小表字号

备份: `backups/v0.10.26/`


## [0.10.25] - 2026-06-13

构建号: `2026.06.13.10`

v0.10.25: _pdf_has_page_rotation加原始字节扫描回退，修复fitz page.rotation返回0的bug

### Changed
- v0.10.25: _pdf_has_page_rotation加原始字节扫描回退，修复fitz page.rotation返回0的bug

备份: `backups/v0.10.25/`


## [0.10.24] - 2026-06-13

构建号: `2026.06.13.9`

v0.10.23: 旋转表格边距改用OSD correction_deg，去P4DBG日志

### Changed
- v0.10.23: 旋转表格边距改用OSD correction_deg，去P4DBG日志

备份: `backups/v0.10.24/`


## [0.10.23] - 2026-06-13

构建号: `2026.06.13.8`

### Fixed
- 旋转单页密集表边距：改用 OSD 视觉检测 `correction_deg` 作为旋转判断条件，替代不可靠的
  `_pdf_has_page_rotation`（Flask 上传 PDF 对 fitz 返回 rotation=0，导致边距始终为 0.45in）
- 合并两个边距覆盖块为一处；去除所有 P4DBG 调试日志

## [0.10.22] - 2026-06-13

构建号: `2026.06.13.7`

### Fixed
- 旋转 PDF 边距修复真正生效：用 `rotated_pdf` 参数替代在 detail_to_docx 内重新调用
  `_pdf_has_page_rotation`（该调用因 fitz 文件句柄状态返回 False 导致边距未设置）

## [0.10.21] - 2026-06-13

构建号: `2026.06.13.6`

### Fixed
- 旋转单页表格行高上限：fallback 路径每行最高 936 twips (0.65in)，防止内容行撑到 1.10in
- 旋转单页表格边距：检测到 /Rotate + img2table 行高时自动应用 WPS 参考边距（左右 1.75in）

## [0.10.20] - 2026-06-13

构建号: `2026.06.13.5`

v0.10.20: scoring form row height atLeast + WPS margins

### Changed
- v0.10.20: scoring form row height atLeast + WPS margins

备份: `backups/v0.10.20/`


## [0.10.19] - 2026-06-13

构建号: `2026.06.13.4`

Fixed: PDF含/Rotate元数据时走逐页PNG模式，避免Volc直传OCR方向错乱

### Fixed
- PDF含/Rotate元数据时走逐页PNG模式，避免Volc直传OCR方向错乱

备份: `backups/v0.10.19/`


## [0.10.18] - 2026-06-13

构建号: `2026.06.13.3`

Fixed: v0.10.17b 从末尾裁剪多余行高（保留顶部小标题行高）

### Fixed
- v0.10.17b 从末尾裁剪多余行高（保留顶部小标题行高）

备份: `backups/v0.10.18/`


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