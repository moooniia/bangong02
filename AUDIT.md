# bangong02.com 全站迁移审计报告

- **日期**：2026-10-20（Asia/Singapore / CST）
- **源站（现网，未改）**：阿里云 `139.196.28.78`（`bangong02.com` DNS 仍指向此处）
- **目标**：腾讯云 109 `43.142.98.170`（`/home/ubuntu/bangong02`）
- **DNS**：未切换
- **审计结论**：**站点主体可切前验收通过**；统计（Umami）与正式 HTTPS 仍须切 DNS 后收尾

---

## 1. 总表（Pass / Fail）

| 项 | 结果 | 说明 |
|----|------|------|
| 前端静态文件对齐 | **PASS** | 非备份文件 176 路径一致，大小全匹配；仅旧机 `.bak*` 未拷（有意） |
| 安装包 /downloads | **PASS**（已补齐） | 6/6 文件 MD5 与旧机一致；公开链接仅用到 `.exe` |
| Flask 上传路径 | **PASS**（已修） | 原先写死 `/home/toolbox/uploads` → 转换 500；已改为 109 路径 |
| toolbox.service | **PASS** | active；`/api/health` → `{"status":"ok"}` |
| nginx :80 / :443 | **PASS** | 自签证书；已补全 Umami location（待容器起来） |
| 页面 HTTP 探测 | **PASS** | 177/177 → 200（含首页、工具页、assets、downloads） |
| sitemap.xml 全部 loc | **PASS** | 39/39 → 200 |
| 备案号页脚 | **PASS** | 42/44 HTML 有 `赣ICP备2026013721号-1` + `beian.miit.gov.cn`；2 个验证页无页脚（正常） |
| 硬编码旧 IP | **PASS** | 前端/后端无 `139.196.28.78` |
| 转换 API 功能 | **PASS** | 见 §4 |
| 公开下载链接 | **PASS** | Installer exe 210013544 B；latest.msix 209919975 B |
| Umami 统计 | **FAIL / 未就绪** | 已装 Docker，拉镜像超时（Docker Hub/ghcr）；`/script.js` 502；`/login` 待容器 |
| 正式 HTTPS（LE） | **待 DNS** | 证书仍在阿里云 Let’s Encrypt |
| 搜索推送 cron | **未迁（有意）** | baidu_push / indexnow 等切 DNS 后再挂 |
| `/claw` OpenClaw | **未迁（有意）** | 非站点本体 |
| favicon.ico | **弱** | 站点用 `/assets/favicon.svg`（有）；裸 `/favicon.ico` 原走 Umami，现 404 |

---

## 2. 旧机清单（阿里云，只读）

### nginx
- `toolbox.conf`：80 → HTTPS；443 `www` 出站；`bangong02.com` 跳 www
- `toolbox-locations.inc`：静态 + Flask `/api/` + Umami（`:3000`）+ `/api/i`
- 另：`8090` 直出 Umami；`/claw` → `18789`（OpenClaw，非本站）

### systemd / 进程
- `nginx`、`toolbox`（Flask :5000）、`openclaw`、`docker`（Umami+db、filebrowser、searxng 等）

### cron（root，站点相关）
- 每 6h / 每日 9:00 `monitor_check.py`
- 03:00 清理 `uploads`/`outputs`
- 04:00 certbot renew
- 06:00 `baidu_push.py`；周一 06:30 `indexnow_push.py`
- 00:05 `generate_stats.py`
- （另有 openclaw 脚本，非站点）

### 数据与证书
- 站点根 `/home/toolbox/`；前端含 `downloads/` ~1.2G
- Let’s Encrypt：`/etc/letsencrypt/live/bangong02.com/`
- Umami compose + docker volume `umami_umami-db`

---

## 3. 相对 109 的差异与已修复

| 遗漏 | 处置 |
|------|------|
| `UPLOAD_FOLDER`/`OUTPUT_FOLDER` 写死 `/home/toolbox/...` | **已修**：默认改为 `/home/ubuntu/bangong02/{uploads,outputs}`，并支持环境变量；重启 `toolbox` |
| `toolbox.env` 默认路径（translate/volc/feedback） | **已修**：默认改为 109 路径 |
| 缺 4 个旧版安装包（~800MB） | **已补**：rsync 自旧机；现 6 文件 MD5 一致 |
| nginx 缺 Umami 路由 | **已补** location（容器未起时仍 502） |
| 无 uploads/outputs 清理 cron | **已加** root 03:00 清理 |
| Umami docker 未装/未起 | **部分**：已 `apt install docker.io`；`compose pull` 因出网超时失败 → **未起** |
| lab | 此前已迁 `/home/ubuntu/bangong02/lab` |
| 备份 `.bak*`、旧 backups、outputs 临时文件 | 未拷（有意） |

### 前端文件对比
- 旧 180 / 新 176（差 4 = 曾缺的 downloads；现已齐，downloads MD5 全匹配）
- 非 downloads：仅旧机 6 个 `.bak*` 独有；同路径 **0** 大小不一致

---

## 4. 功能 API 测试（109 本机，经 Flask / nginx）

样本：最小 PDF / DOCX / PNG。均 `success:true`，`/api/download/<file>` 200，且 `file(1)` 类型正确。

| 接口 | 结果 | 产出校验 |
|------|------|----------|
| `POST /api/convert` PDF→docx | PASS | Word 2007+ (PK…) ~43KB；route=`volc-hybrid` |
| 同上（经 nginx Host） | PASS | 同上 |
| `POST /api/convert` DOCX→pdf | PASS | PDF 1.7，1 页 |
| PDF→xlsx / pptx | PASS | Excel/PPTX OOXML |
| `POST /api/pdf/merge` | PASS | PDF 2 页 |
| `POST /api/pdf/compress` | PASS | PDF |
| `POST /api/images/to-pdf` | PASS | PDF |
| `POST /api/image/compress` | PASS（此前） | jpg |
| `GET /api/health` | PASS | ok |
| OCR 纯色小图 | 400 预期 | 「未识别到文字」 |

公开下载（HEAD/GET）：
- `/downloads/InvoiceToolboxInstaller-1.0.0.60.exe` → 200，210013544
- `/downloads/InvoiceToolbox.WinUI_latest.msix` → 200，209919975  
页面仅引用 **Installer exe**。

---

## 5. 备案号

- 业务 HTML（不含百度/谷歌验证页）：**均有** `赣ICP备2026013721号-1`，链接 `https://beian.miit.gov.cn/`
- `/baidu_verify_*.html`、`/google*.html`：无页脚（验证文件，正常）

---

## 6. 切 DNS 前 / 后仍待办

### 切 DNS 前（可选）
1. Umami：配国内镜像或从旧机 `docker save` 导入 `postgres:15-alpine` + `umami` 镜像后 `compose up`；历史数据需另迁 volume（风险较高，可新库）
2. 人工浏览器再点几轮真实大文件转换
3. （可选）把旧机 `favicon.ico` 落到前端，避免依赖 Umami

### 切 DNS 时/后（必须）
1. A 记录 `bangong02.com` / `www` → `43.142.98.170`
2. 109 上申请 Let’s Encrypt，替换自签；打开 80/443 校验
3. 挂 baidu_push / indexnow / generate_stats / monitor cron（路径改到 `/home/ubuntu/bangong02`）
4. Umami 域名与 COLLECT 端点确认；旧机 Umami 可停
5. 确认腾讯云防火墙 80/443；旧机可保留回滚窗口再下线 nginx 站点

### 明确不搬
- OpenClaw `/claw`、filebrowser、searxng、mihomo 等非 bangong02 站点组件

---

## 7. 自测入口（DNS 未切）

- HTTP：http://43.142.98.170/
- HTTPS（自签，需忽略警告）：https://43.142.98.170/
- Host 头 `bangong02.com` 亦可

---

## 8. 变更摘要（仅 109，未动阿里云现网）

1. 修补 `backend/app.py` 与 env 默认路径并 restart `toolbox`
2. rsync 补齐 4 个历史安装包
3. nginx 补 Umami 相关 location；reload
4. 安装 Docker；Umami 镜像拉取失败未启动
5. 添加 uploads/outputs 日清理 cron
